import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from data_management.models import Student


def try_parse_date(value):
    """Try several common date formats, return a date object (isoformat) or None."""
    if not value:
        return None
    value = value.strip()
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            continue
    # last resort, try ISO parse
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def parse_bool(value):
    if value is None:
        return False
    v = str(value).strip().lower()
    if v in ("1", "true", "t", "yes", "y", "on"):
        return True
    if v in ("0", "false", "f", "no", "n", "off"):
        return False
    return False


def to_decimal(value):
    if value is None or value == "":
        return None
    try:
        # Remove common thousand separators
        v = str(value).replace(",", "")
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "Seed students from a CSV file. CSV headers must match Student fields + username/email columns."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to CSV file")
        parser.add_argument(
            "--update", action="store_true", help="Update existing records when found"
        )
        parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")

    def handle(self, *args, **options):
        csv_path = options["csv"]
        do_update = options["update"]
        delimiter = options["delimiter"]

        User = get_user_model()

        # Only map CSV columns to actual concrete Student model fields.
        student_model_fields = {
            f.name
            for f in Student._meta.get_fields()
            if getattr(f, "concrete", True)
            and not getattr(f, "many_to_many", False)
            and not getattr(f, "auto_created", False)
        }

        # fields we expect (based on provided index + user fields)
        expected_fields = [
            "email",
            "full_name",
            "passport_number",
            "lapdik_number",
            "birth_place",
            "birth_date",
            "gender",
            "arrival_date",
            "school_origin",
            "marital_status",
            "region_origin",
            "whatsapp_number",
            "institution",
            "faculty",
            "major",
            "degree_level",
            "semester_level",
            "latest_grade",
            "home_name",
            "home_location",
            "parents_name",
            "parents_phone",
            "guardian_name",
            "guardian_phone",
            "education_funding",
            "living_cost",
            "monthly_income",
            "photo_url",
            "username",
            "disease_history",
            "disease_status",
            "sport_interest",
            "sport_achievement",
            "art_interest",
            "art_achievement",
            "literacy_interest",
            "literacy_achievement",
            "science_interest",
            "science_achievement",
            "mtq_interest",
            "mtq_achievement",
            "media_interest",
            "media_achievement",
            "organization_history",
            "scholarship_source",
            "level",
            "is_draft",
        ]

        created_users = 0
        updated_users = 0
        created_students = 0
        updated_students = 0
        skipped = 0
        errors = []

        try:
            f = open(csv_path, newline="", encoding="utf-8")
        except Exception as e:
            raise CommandError(f"Could not open CSV file: {e}")

        reader = csv.DictReader(f, delimiter=delimiter)
        # normalize headers: strip spaces
        headers = [h.strip() if h else h for h in reader.fieldnames]
        # detect duplicate headers
        lower_seen = {}
        duplicates = []
        for i, h in enumerate(headers):
            key = h.lower() if h else h
            if key in lower_seen:
                duplicates.append(h)
            else:
                lower_seen[key] = h
        if duplicates:
            self.stdout.write(
                self.style.WARNING(
                    f"Duplicate headers detected: {duplicates}. Using first occurrence."
                )
            )

        row_number = 0
        for raw_row in reader:
            row_number += 1
            # map normalized headers -> values
            row = {}
            for k, v in raw_row.items():
                if k is None:
                    continue
                nk = k.strip()
                if nk == "":
                    continue
                if nk.lower() in row:
                    # skip duplicates
                    continue
                row[nk] = v.strip() if isinstance(v, str) else v

            # Extract key identifiers
            username = None
            email = None
            # find keys case-insensitive
            for key in row.keys():
                lk = key.lower()
                if lk == "username":
                    username = row[key]
                if lk == "email":
                    # prefer first email column
                    if not email:
                        email = row[key]

            if not username and email:
                # derive username from email local-part
                username = email.split("@")[0]

            if not username and not email:
                errors.append((row_number, "missing username and email"))
                skipped += 1
                continue

            # find or create user
            try:
                user = None
                if username:
                    try:
                        user = User.objects.get(username=username)
                    except User.DoesNotExist:
                        user = None
                if user is None and email:
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        user = None

                if user is None:
                    # create user
                    first_name = ""
                    last_name = ""
                    full_name_val = None
                    # try to find full_name in row
                    for key in row.keys():
                        if key.lower() == "full_name":
                            full_name_val = row[key]
                            break
                    if full_name_val:
                        parts = full_name_val.split()
                        first_name = parts[0]
                        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

                    # try to create with create_user if available
                    password = (
                        User.objects.make_random_password()
                        if hasattr(User.objects, "make_random_password")
                        else None
                    )
                    try:
                        if hasattr(User.objects, "create_user"):
                            user = User.objects.create_user(
                                username=username, email=email or "", password=password
                            )
                        else:
                            user = User.objects.create(username=username, email=email or "")
                            if password:
                                user.set_password(password)
                                user.save()
                    except Exception as e:
                        errors.append((row_number, f"user create error: {e}"))
                        skipped += 1
                        continue

                    if full_name_val:
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                    created_users += 1
                else:
                    # user exists
                    if do_update:
                        changed = False
                        full_name_val = None
                        for key in row.keys():
                            if key.lower() == "full_name":
                                full_name_val = row[key]
                                break
                        if full_name_val:
                            parts = full_name_val.split()
                            fn = parts[0]
                            ln = " ".join(parts[1:]) if len(parts) > 1 else ""
                            if user.first_name != fn or user.last_name != ln:
                                user.first_name = fn
                                user.last_name = ln
                                changed = True
                        if email and user.email != email:
                            user.email = email
                            changed = True
                        if changed:
                            user.save()
                            updated_users += 1

                # Prepare student defaults mapping
                student_defaults = {}
                # Map fields
                for field in expected_fields:
                    # skip fields that are not actual Student model fields (e.g. email, full_name, username)
                    if field not in student_model_fields:
                        continue
                    # find csv header that matches field (case-insensitive)
                    found = None
                    for h in row.keys():
                        if h.lower() == field.lower():
                            found = row[h]
                            break
                    if found is None:
                        continue
                    val = found
                    if val == "":
                        val = None

                    # coerce types based on field
                    if field in ("birth_date", "arrival_date"):
                        student_defaults[field] = try_parse_date(val)
                    elif field in ("semester_level",):
                        try:
                            student_defaults[field] = int(val) if val is not None else None
                        except Exception:
                            student_defaults[field] = None
                    elif field in ("latest_grade", "living_cost", "monthly_income"):
                        student_defaults[field] = to_decimal(val)
                    elif field == "is_draft":
                        student_defaults[field] = parse_bool(val)
                    else:
                        # strings and choices
                        if val is not None:
                            student_defaults[field] = val

                # Ensure required non-nullable fields have defaults
                if (
                    "semester_level" not in student_defaults
                    or student_defaults.get("semester_level") is None
                ):
                    student_defaults["semester_level"] = 1
                if "degree_level" not in student_defaults or not student_defaults.get(
                    "degree_level"
                ):
                    # default to S1 if not provided
                    student_defaults["degree_level"] = "S1"

                # find existing student by user or passport_number
                student = None
                try:
                    student = Student.objects.get(user=user)
                except Student.DoesNotExist:
                    # try passport
                    pnum = student_defaults.get("passport_number")
                    q = Q()
                    if pnum:
                        q |= Q(passport_number=pnum)
                    if q:
                        try:
                            student = Student.objects.get(q)
                        except Student.DoesNotExist:
                            student = None
                        except Student.MultipleObjectsReturned:
                            student = None

                if student is not None:
                    if do_update:
                        for k, v in student_defaults.items():
                            setattr(student, k, v)
                        try:
                            with transaction.atomic():
                                student.full_clean()
                                student.save()
                            updated_students += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Row {row_number}: Updated student for user {user.username}"
                                )
                            )
                        except ValidationError as ve:
                            errors.append(
                                (row_number, f"student validation error: {ve.message_dict}")
                            )
                            skipped += 1
                        except Exception as e:
                            errors.append((row_number, f"student save error: {e}"))
                            skipped += 1
                    else:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {row_number}: Student already exists for user {user.username} (skipped). Use --update to overwrite."
                            )
                        )
                else:
                    # create new
                    try:
                        with transaction.atomic():
                            student = Student.objects.create(user=user, **student_defaults)
                        created_students += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Row {row_number}: Created student for user {user.username}"
                            )
                        )
                    except ValidationError as ve:
                        errors.append((row_number, f"student validation error: {ve.message_dict}"))
                        skipped += 1
                    except Exception as e:
                        errors.append((row_number, f"student create error: {e}"))
                        skipped += 1

            except Exception as e:
                errors.append((row_number, f"unhandled error: {e}"))
                skipped += 1
                continue

        f.close()

        # Summary
        self.stdout.write("\n")
        self.stdout.write(
            self.style.SUCCESS(f"Users created: {created_users}, updated: {updated_users}")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Students created: {created_students}, updated: {updated_students}, skipped: {skipped}"
            )
        )
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors ({len(errors)}):"))
            for rnum, msg in errors[:20]:
                self.stdout.write(self.style.ERROR(f"  Row {rnum}: {msg}"))
            if len(errors) > 20:
                self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 20} more errors"))

        return 0
