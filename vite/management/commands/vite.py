import os.path
import shutil
import subprocess

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from vite import NpmManager


class Command(BaseCommand):
    help = "Vite management command"

    @staticmethod
    def get_app_cwd(app_name):
        app_config = apps.get_app_config(app_name)
        app_path = app_config.path
        return os.path.abspath(app_path)

    def add_arguments(self, parser):
        parser.add_argument("package_name", type=str, help="NPM package name to install")

    def handle(self, *args, **options):
        subcommand = options.get("package_name")

        if subcommand == "dev":
            self.handle_dev()
        else:
            self.stdout.write(self.style.ERROR(f"Unknown subcommand: {subcommand}"))

    def handle_dev(self):
        django_dir = settings.BASE_DIR
        vite_dir = self.get_app_cwd(app_name="vite")
        vite_server = NpmManager(cwd=f"{vite_dir}/src")

        if not vite_server.is_npm_installed():
            self.stdout.write(self.style.ERROR("npm is not installed"))
            return

        # Check if Honcho is available
        if shutil.which("honcho"):
            try:
                self.stdout.write(self.style.SUCCESS("Starting Vite and Django with Honcho..."))
                self.stdout.write(self.style.WARNING("Press Ctrl+C to stop all processes.\n"))

                # Run honcho start in the project root
                subprocess.run(["honcho", "start"], cwd=django_dir, check=True)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n\nStopping processes..."))
            except subprocess.CalledProcessError as e:
                self.stdout.write(self.style.ERROR(f"Honcho failed with error: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            finally:
                self.stdout.write(self.style.SUCCESS("Processes stopped."))
        else:
            self.stdout.write(
                self.style.ERROR("Honcho is not installed. Please install it with: uv add honcho")
            )
