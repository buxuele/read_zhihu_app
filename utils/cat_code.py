import os
from pathlib import Path

# 目的：为了与 AI 交流更方便，
# 将项目中所有代码和文件内容输出到一个地方，集中管理。

def list_and_print_files():
    # 获取当前目录
    current_dir = Path.cwd()
    # 要排除的文件和目录列表
    exclude_items = [".git", ".idea", "__pycache__",
                     ".gitignore", "venv", ".env",  
                     "read_venv",
                     "gg.bat","data", "good_stuff",
                     "my_files.txt", "cat_code.py",
                     "过程记录.md", "README.md", "readme.md", 
                     "gist_venv"]
    # 输出文件
    output_file = "my_files.txt"

    # 打开输出文件以写入结果
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # 遍历当前目录
        for root, dirs, files in os.walk(current_dir, topdown=True):
            # 排除指定的目录
            dirs[:] = [d for d in dirs if d not in exclude_items]
            # 排除指定的文件
            files[:] = [f for f in files if f not in exclude_items]

            # 处理当前目录中的每个文件
            for name in files:
                file_path = Path(root) / name
                # 获取相对路径以便输出更简洁
                relative_path = file_path.relative_to(current_dir)
                # 格式化输出
                output = f"\n文件: {relative_path}\n"
                print(output.strip())  # 打印到控制台
                out_f.write(output)  # 写入文件

                # 检查文件是否为空
                if file_path.stat().st_size == 0:
                    output = "内容: 此文件为空\n"
                    print(output.strip())
                    out_f.write(output)
                    continue

                try:
                    # 尝试以文本形式读取文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip() == "":
                            output = "内容: 此文件为空\n"
                        else:
                            output = f"内容:\n{content}\n"
                        print(output.strip())  # 打印到控制台
                        out_f.write(output)  # 写入文件
                except UnicodeDecodeError:
                    output = "内容: [无法作为文本读取，可能是二进制文件]\n"
                    print(output.strip())
                    out_f.write(output)
                except PermissionError:
                    output = "内容: [权限被拒绝]\n"
                    print(output.strip())
                    out_f.write(output)
                except Exception as e:
                    output = f"内容: [读取文件出错: {e}]\n"
                    print(output.strip())
                    out_f.write(output)

            # 处理当前目录中的每个子目录
            for name in dirs:
                dir_path = Path(root) / name
                # 获取相对路径
                relative_path = dir_path.relative_to(current_dir)
                # 格式化输出
                output = f"\n目录: {relative_path}\n"
                print(output.strip())  # 打印到控制台
                out_f.write(output)  # 写入文件

                # 检查目录是否为空
                is_empty = True
                for _ in dir_path.iterdir():
                    is_empty = False
                    break
                if is_empty:
                    output = "内容: 此目录为空\n"
                else:
                    output = "内容: [这是一个目录]\n"
                print(output.strip())  # 打印到控制台
                out_f.write(output)  # 写入文件

if __name__ == "__main__":
    list_and_print_files()