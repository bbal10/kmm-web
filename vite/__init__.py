import os
import subprocess

from django.conf import settings


def get_config(setting_name):
    vite_dev_server_url = getattr(settings, "VITE_DEV_SERVER_URL", "http://localhost:5173")
    config = {
        "NPM_BIN_PATH": getattr(settings, "NPM_BIN_PATH", "npm"),
        "VITE_DEV_SERVER_URL": vite_dev_server_url,
        "VITE_DEV_MODE": getattr(settings, "VITE_DEV_MODE", True),
        "VITE_JS_ENTRYPOINT": getattr(
            settings, "VITE_JS_ENTRYPOINT", f"{vite_dev_server_url}/src/index.ts"
        ),
        "VITE_CSS_ENTRYPOINT": getattr(
            settings, "VITE_CSS_ENTRYPOINT", f"{vite_dev_server_url}/src/style.css"
        ),
        "VITE_MANIFEST_PATH": getattr(
            settings,
            "VITE_MANIFEST_PATH",
            os.path.join(settings.BASE_DIR, "vite", "static", "dist", ".vite", "manifest.json"),
        ),
    }

    return config[setting_name]


class NpmManager:
    def __init__(self, cwd=None):
        """
        cwd: Direktori kerja untuk menjalankan perintah npm (default: direktori saat ini)
        """
        self.cwd = cwd or os.getcwd()
        self._ensure_cwd_exists()

    def _ensure_cwd_exists(self):
        if not os.path.exists(self.cwd):
            try:
                os.makedirs(self.cwd)
                print(f"Direktori '{self.cwd}' berhasil dibuat.")
            except Exception as e:
                print(f"Gagal membuat direktori '{self.cwd}': {e}")
                raise

    def is_npm_installed(self):
        try:
            subprocess.run(
                ["npm", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            return True
        except FileNotFoundError:
            print(
                "npm tidak ditemukan! Pastikan Node.js dan npm sudah terinstall dan path sudah benar."
            )
            return False
        except subprocess.CalledProcessError as e:
            print("Error saat menjalankan npm:", e)
            return False

    def run_command(self, args, return_process=False):
        if not self.is_npm_installed():
            return False

        try:
            if return_process and args == ["npm", "run", "dev"]:
                process = subprocess.Popen(
                    args, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                print(f"Perintah {' '.join(args)} berhasil dijalankan (Popen).")
                return process
            elif args == ["npm", "run", "dev"]:
                process = subprocess.Popen(
                    args, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                print(f"Perintah {' '.join(args)} berhasil dijalankan (Popen).")
                print("Output:", process.stdout)
                return True
            else:
                result = subprocess.run(
                    args,
                    cwd=self.cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
                print(f"Perintah {' '.join(args)} berhasil dijalankan.")
                print("Output:", result.stdout)
                return True
        except subprocess.CalledProcessError as e:
            print(f"Gagal menjalankan {' '.join(args)}:")
            print("Stdout:", e.stdout)
            print("Stderr:", e.stderr)
            return False
        except Exception as ex:
            print(f"Terjadi error lain: {ex}")
            return False

    def npm_install(self):
        return self.run_command(["npm", "install"])

    def npm_run_dev(self):
        return self.run_command(["npm", "run", "dev"], return_process=True)

    def npm_run_build(self):
        return self.run_command(["npm", "run", "build"])

    def npm_install_package(self, package_name):
        return self.run_command(["npm", "install", package_name])
