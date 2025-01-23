import pandas as pd

# Charger le fichier Excel
file_path = './extracted_delivery/1945 USAAF Serial Numbers.xlsx'
df = pd.read_excel(file_path)

# Convertir les numéros de série en entiers, en filtrant les NaN
df.iloc[:, 0] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
df = df.dropna(subset=[df.columns[0]])
df.iloc[:, 0] = df.iloc[:, 0].astype(int)

# Extraire les numéros de série
serial_numbers = df.iloc[:, 0]

# Trouver les numéros de série manquants
min_serial = serial_numbers.min()
max_serial = serial_numbers.max()
all_serials = set(range(min_serial, max_serial + 1))
existing_serials = set(serial_numbers)
missing_serials = all_serials - existing_serials

# Ajouter les lignes manquantes
for missing_serial in sorted(missing_serials):
    df = df.append({df.columns[0]: missing_serial, df.columns[1]: 'N/A'}, ignore_index=True)

# Trier le DataFrame par la colonne des numéros de série
df = df.sort_values(by=df.columns[0]).reset_index(drop=True)

# Sauvegarder le fichier mis à jour
output_file_path = './extracted_delivery/1945 USAAF Serial Numbers - Updated.xlsx'
df.to_excel(output_file_path, index=False)