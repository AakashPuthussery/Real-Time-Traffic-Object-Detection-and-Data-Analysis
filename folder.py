import os
import argparse

def display_folder_structure(startpath, indent=0):
    excluded_folders = {"myenv", "__pycache__"}
    
    for item in os.listdir(startpath):
        item_path = os.path.join(startpath, item)
        if os.path.isdir(item_path) and item in excluded_folders:
            continue
        
        print('    ' * indent + '|-- ' + item)
        if os.path.isdir(item_path):
            display_folder_structure(item_path, indent + 1)

def main():
    parser = argparse.ArgumentParser(description="Display folder structure in a tree format.")
    parser.add_argument("path", nargs='?', default=os.getcwd(), help="Path to the folder (default: current directory)")
    args = parser.parse_args()
    
    if os.path.exists(args.path) and os.path.isdir(args.path):
        print(args.path)
        display_folder_structure(args.path)
    else:
        print("Invalid folder path.")

if __name__ == "__main__":
    main()