import subprocess
import sys
import os
import venv


def setup_environment():
    project_root = os.getcwd()
    venv_path = os.path.join(project_root, "venv")

    print(f"Creating venv in {venv_path}...")
    venv.create(venv_path, with_pip=True)

    # Определяем путь к pip внутри venv
    if sys.platform == "win32":
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")
        python_path = os.path.join(venv_path, "bin", "python")

    # Обновляем pip
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"])

    # Устанавливаем базовые пакеты для тестирования
    packages = ["pytest", "pytest-cov", "requests"]
    subprocess.run([pip_path, "install"] + packages)

    print("Environment setup complete!")


if __name__ == "__main__":
    setup_environment()
