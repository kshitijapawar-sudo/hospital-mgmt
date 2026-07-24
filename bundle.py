import os
import zipfile

def create_bundle():
    zip_name = "hospital-mgmt-dist.zip"
    print(f"Creating distribution bundle: {zip_name}...")

    # We get the root directory where bundle.py is located
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'env'}
    exclude_files = {
        zip_name, 
        'hospital.db', 
        'hospital.db-journal', 
        'hospital.db-wal', 
        'hospital.db-shm',
        '.gitignore',
        'bundle.py',
        'create_bundle.bat'
    }

    files_added = 0
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to avoid traversing excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                # Also exclude any other zip files
                if file.endswith('.zip'):
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, root_dir)
                
                print(f"  Adding: {rel_path}")
                zipf.write(abs_path, rel_path)
                files_added += 1

    zip_size_kb = os.path.getsize(zip_name) / 1024
    print(f"\nSuccessfully created {zip_name}!")
    print(f"Total files added: {files_added}")
    print(f"Bundle size: {zip_size_kb:.2f} KB")

if __name__ == "__main__":
    create_bundle()
