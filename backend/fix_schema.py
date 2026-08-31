import os
import re

routes_dir = r'app\routes'
for fname in os.listdir(routes_dir):
    if fname.endswith('.py'):
        fpath = os.path.join(routes_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content.replace("supabase.schema('bar_mune').table(", "supabase.table(")
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated: {fname}")
        else:
            print(f"No changes: {fname}")

print("Done.")
