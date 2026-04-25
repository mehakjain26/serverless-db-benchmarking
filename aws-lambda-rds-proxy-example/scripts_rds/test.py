import os

def count_lines(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return sum(1 for _ in file)

def file_size_mb(filename):
    size_bytes = os.path.getsize(filename)
    return size_bytes / (1024 * 1024)  # convert to MB

file = "stop_times.txt"
test_file = [
    f'columbus/{file}', f'chicago/{file}',
    f'lafayette/{file}',
    f'atlanta/{file}'
]

for file_path in test_file:
    lines = count_lines(file_path)
    size_mb = file_size_mb(file_path)
    print(f"{file_path}: {lines:,} lines, {size_mb:.2f} MB")