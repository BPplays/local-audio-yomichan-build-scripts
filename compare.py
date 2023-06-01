import os
import filecmp
import sys

"""
Display files which are the same between jpod_files and jpod_alternative_files
"""

jpod_files = os.listdir('jpod_files')
jpod_alternate_files = os.listdir('jpod_alternate_files')

common_files = []

for file in set(jpod_files).intersection(jpod_alternate_files):
    if filecmp.cmp(f'jpod_files/{file}', f'jpod_alternate_files/{file}', shallow=False):
        if sys.argv[1] == "delete":
            os.remove(f'jpod_alternate_files/{file}')
            print(f"deleted jpod_alternate_files/{file}")
        else:
            common_files.append(file)

if sys.argv[1] != "delete":
    with open('common_files_same_hash.txt', 'w') as file:
        file.write('\n'.join(common_files))
