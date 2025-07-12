import sys
import os
import subprocess
from pathlib import Path


def render_puml_files(target_dir: str, out_format: str):
    if out_format not in ("svg", "png"):
        print(f"[ERROR] Неподдерживаемый формат: {out_format}. Используйте svg или png.")
        sys.exit(2)

    target = Path(target_dir)
    if not target.is_dir():
        print(f"[ERROR] Директория {target_dir} не существует.")
        sys.exit(1)

    puml_files = list(target.rglob("*.puml"))
    if not puml_files:
        print(f"[INFO] Не найдено .puml файлов в {target_dir}")
        return

    print(f"[INFO] Найдено {len(puml_files)} .puml файлов. Начинаю рендеринг в {out_format}...")
    for puml_file in puml_files:
        out_file = puml_file.with_suffix(f'.{out_format}')
        cmd = [
            "java", "-jar", "/opt/plantuml.jar",
            f"-t{out_format}", str(puml_file)
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if out_file.exists():
                print(f"[OK] {out_file}")
            else:
                print(f"[FAIL] {puml_file} — SVG/PNG не создан")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] {puml_file}: {e.stderr.decode(errors='ignore')}")

    print("[INFO] Рендеринг завершён.")


def get_mount_point():
    """Получает точку монтирования из переменной окружения или использует значение по умолчанию"""
    return os.getenv('MOUNT_POINT', '/workspace')


def main():
    mount_point = get_mount_point()

    if len(sys.argv) != 3:
        print("Использование: python render_plantuml.py <путь_к_папке> <svg|png>")
        print(f"Пример: python render_plantuml.py {mount_point}/docs/architecture/diagrams svg")
        print("")
        print("Переменные окружения:")
        print(f"  MOUNT_POINT={mount_point} (точка монтирования)")
        print("")
        print("Примеры запуска:")
        print("  # Используя пути как в репозитории:")
        print("  export MOUNT_POINT='/workspace'")
        print("  docker run --rm -v \$(pwd):\$MOUNT_POINT plantuml-renderer \$MOUNT_POINT/docs/architecture/diagrams svg")
        print("")
        print("  # Или с другой точкой монтирования:")
        print("  export MOUNT_POINT='/repo'")
        print("  docker run --rm -v \$(pwd):\$MOUNT_POINT plantuml-renderer \$MOUNT_POINT/docs/architecture/diagrams png")
        sys.exit(1)

    render_puml_files(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()