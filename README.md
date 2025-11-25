

0

pre:

windows:
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12



1
packages extern


windows:

winget install -e --id UB-Mannheim.TesseractOCR
winget install -e --id oschwartz10612.Poppler
winget install -e --id ArtifexSoftware.Ghostscript

linux

sudo apt-get install tesseract-ocr tesseract-ocr-all
sudo apt-get install poppler-utils
sudo apt install ghostscript


2 

pip install -r requirement.txt




3
set user name and pw:

mac:
echo '{"username": "", "password": "", "USERNAME_popup": "", "PASSWORD_popup": ""}' > credentials.json

linux:




windows:

echo '{"username": "", "password": "", "USERNAME_popup": "", "PASSWORD_popup": ""}' | Out-File -FilePath credentials.json -Encoding utf8

4

execute:

python main.py --config bwl_master_config
python main.py --config ai_master_config

5

#1 = url aenderungen notwendig fuer produktivsystem
#2 = sleep kann entfernt werden , da kein popup

