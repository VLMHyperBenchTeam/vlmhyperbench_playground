import os
import sys


def list_dir(path, indent="", limit=5):
    items = sorted(os.listdir(path))
    count = 0
    for item in items:
        full_path = os.path.join(path, item)
        if count >= limit:
            print(f"{indent}└── ... ({len(items)-limit} more)")
            break

        prefix = "├──" if count < len(items)-1 else "└──"
        print(f"{indent}{prefix} {item}")

        if os.path.isdir(full_path):
            new_indent = indent + ("│   " if count < len(items)-1 else "    ")
            list_dir(full_path, new_indent, limit)

        count += 1

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(root)
    list_dir(root, limit=5)