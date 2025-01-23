import bs4
import re
import chardet
import pandas as pd
from pathlib import Path
import time
import os

## Variables globales
filename = ""

## get_first_serial_number_of_document
def get_first_serial_number_of_document(filename):
    if '(' in filename:
        return int(filename.split('-')[1].split(' to')[0])
    else:
        return 1
## Calcul du temps écoulé
def get_elapsed_time():
    time_end = time.time()
    elapsed_time = (time_end - time_start)
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    # écris la même instruction print mais avec f""
    print(f"Elapsed time to extract information: {int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds\n")

## Detect encoding type of document
def encoding_detect(filename):
    ## Détecter le codage du fichier
    # Lire le contenu binaire du fichier
    with open(filename, "rb") as file:
        raw_data = file.read(100000)  # lire les premiers 100 000 octets pour estimer l'encodage
    # Utiliser chardet pour détecter l'encodage
    encoding = chardet.detect(raw_data)['encoding']
    # print(encoding)
    return  "ISO-8859-1" #encoding |

## Récupérer le contenu HTML
def get_html_content(filename):
    # Chargement du contenu HTML à partir d'un fichier local
    encoding = encoding_detect(filename)
    with open(filename, "r", encoding=encoding) as file:
        content = file.read()
    # BS pour analyser le contenu HTML
    soup = bs4.BeautifulSoup(content, 'html.parser')
    # Trouver la partie du contenu qui contient les informations
    data_text = soup.find('pre').text
    # print(data_text)
    return data_text

## Découpage en grands blocs
def parse_main_entries(data_text):
    # Organiser les résultats dans un dictionnaire
    data_dict = {}
    pattern = re.compile(r'^(\d+-\d+(?:\/\d+)?)([\s\S]+?)(?=\n\d+-\d+(?:\/\d+)?\s|\Z)', re.MULTILINE)
    matches = pattern.findall(data_text)
    blocks_number = int(len(matches))
    # print(matches)

    for match in matches:
        key = match[0]
        rest = match[1].strip()
        first_line_break = rest.find('\n')  # Trouver la fin de la première ligne après le numéro de série
        if first_line_break == -1:
            data_dict[key] = {'type': rest, 'details': ""}
        else:
            type_description = rest[:first_line_break]  # Le type est sur la même ligne que le numéro de série
            details = rest[first_line_break:]  # Les détails commencent après la première ligne
            data_dict[key] = {'type': type_description, 'details': details}
    # Retourner le dictionnaire
    return data_dict, blocks_number


## Affichage des grands blocs
def display_main_entries(data_dict):
    # Afficher les grands blocs avec le type d'avion et les détails
    for key, content in data_dict.items():
        print(f"Numéro de série principal: {key}\t\tType d'avion: {content['type']}")
        if isinstance(content['details'], dict):  # Si les détails contiennent des sous-numéros de série
            for sub_key, description in content['details'].items():
                print(f"    Sous-numéro de série: {sub_key}, Description: {description}")
        else:  # Si le contenu des détails est juste une chaîne de caractères (pas de sous-numéros)
            print(f"    Détails: {content['details']}")
        print("\n")


def parse_sub_entries(data_dict):
    # Pour chaque grand bloc, parsez les informations spécifiques par numéro de série interne
    detailed_dict = {}

    # Analyze details for each major block
    for key, content in data_dict.items():
        type_info = content['type']
        details = content['details']
        # print(key, type_info, details)
        sub_dict = {}
        # Cas où il n'y a pas de sous-numéros de série (une seule ligne dont type ou i.e contrat annulé)
        if details == "":
            # print("Sous-cas sans sous-numéros de série")
            if "/" in key:
                start = key.split('-')[1].split('/')[0]
                end = key.split('-')[1].split('/')[1]
                for i in range(int(start), int(end) + 1):
                    sub_dict[f"{key.split('-')[0]}-{i}"] = type_info
            else:
                sub_dict[key] = type_info
            detailed_dict[key] = {'build': "", 'type': "", 'details': sub_dict}
        # Cas d'une plage de numéros de série pour le grand bloc
        if '/' in key:
            # print(key, type_info, details)
            base_number = key.split('-')[0]
            # # Find all sub-serial numbers in the details including singletons, ranges all on separated lines
            # Regex to explicitly identify sub-serial numbers in details considering possible tabs
            sub_pattern = re.compile(r'(?:\t{2})(\d+(?:\/(\d+))?)\s+(.*?)(?=\t{4}(\d+(?:\/\d+)?)\s+|$)',
                                     re.DOTALL)  # \t(\d+)(?:\/(\d+))?\s+((?:.|\n)+?)(?=(\n\t\d+|$))
            sub_matches = sub_pattern.finditer(details)
            # prev_serial serves as detection of potential numbers detected by the regex, however not supposed to be considered as a serial number
            prev_serial = key.split('-')[1].split('/')[0]
            # print("Prev serial, debut de grand bloc: ", prev_serial)
            for match in sub_matches:
                # print(match.group(1), prev_serial, match.group(3))
                ## Cas où ce n'est pas une plage de sous-numéros
                if match.group(2) is None:
                    delta = abs(int(match.group(1)) - int(prev_serial))
                    # print("Ecart: ", delta)
                    if delta < 160:
                        # Cas où les deux chiffres sont proches
                        # print("Cas sans plage / écart < 50, écart:", abs(int(match.group(1)) - int(prev_serial)))
                        sub_num = match.group(1)
                        # print(sub_num)
                        description = match.group(3).strip()
                        sub_key= f"{base_number}-{sub_num}"
                        sub_dict[sub_key] = description
                        prev_serial = sub_num
                        # print("changement de prev_serial", prev_serial)
                        # print(type(sub_key), sub_key)
                    else:
                        # Cas où les deux chiffres sont éloignés, ne pas perturber le cycle par un nombre en début de phrase mais qui n'est pas un numéro de série à capturer
                        sub_key = f"{base_number}-{prev_serial}"
                        # print(sub_key)
                        if bool(sub_dict):
                            # Vérification que sub_dict n'est pas vide pour que la sub_key existe

                            # print("Cas sans plage / écart >= 30", "sub_key", sub_key, "prev_serial", prev_serial, match.group(1), " / ", match.group(3).strip())
                            sub_dict[sub_key] += match.group(1) + " " + match.group(3).strip()
                        else:
                            # Cas où sub_dict est vide, on ne peut pas ajouter un numéro de série à une clé qui n'existe pas
                            sub_dict[sub_key] = match.group(1) + " " + match.group(3).strip()
                            # print("Cas sans plage / écart >= 30", "sub_key", f"{base_number}-{prev_serial}", "prev_serial", prev_serial, match.group(1), " / ", match.group(3).strip(), match)

                # Cas où c'est une plage de sous-numéros
                else:
                    # Cas où les deux chiffres de la plage sont de la même longueur dont des numéros de série consécutifs mais à incrémenter
                    sub = match.group(1).split('/')[0]
                    if len(sub) == len(match.group(2)):
                        # print("Cas avec plage / numéro du même type")
                        for i in range(int(sub), int(match.group(2)) + 1):
                            sub_key = f"{base_number}-{i}"
                            sub_dict[sub_key] = match.group(3).strip()

                        prev_serial = match.group(2)
                        # print("changement de prev_serial", prev_serial)
                    # Cas où il s'agit d'un incrément depuis le premier numéro de la plage
                    if len(match.group(2)) == 1:
                        # print("Cas avec plage / numéro pas même type")
                        for i in range(int(match.group(2)) + 1):
                            sub_key = f"{base_number}-{int(sub) + i}"
                            sub_dict[sub_key] = match.group(3).strip()

                        prev_serial = str(int(sub) + int(match.group(2)))
                        # print("changement de prev_serial", prev_serial)


                # # Look for serial numbers multiple ranges or singletons that are all described in the same sub section
                sub_pattern = re.compile(r'\t((\d+\/\d+,\s)+)((\d+(\/\d+)?[,\s\n]+))+(.*?)(?=\n)(?:\t\d+|$)',
                                         re.MULTILINE)
                sub_matches = sub_pattern.finditer(details)
                if sub_matches:
                    for match in list(sub_matches):
                        string = match.group(0).strip()
                        parts = re.split(r'(?<=\d)(?=\s+[a-zA-Z])', string, maxsplit=1)

                        if len(parts) == 2:
                            serials_part, description = parts
                            # Étape 2: Extraire tous les numéros de série ou plages à partir de la partie précédente
                            serials_list = re.findall(r'\d+(?:/\d+)?', serials_part)

                            for serial in serials_list:
                                if "/" in serial:
                                    serial_parts = serial.split("/")
                                    for i in range(int(serial_parts[0]), int(serial_parts[1]) + 1):
                                        sub_dict[f"{base_number}-{str(i)}"] = description.strip()
                                else:
                                    sub_dict[f"{base_number}-{int(serial)}"] = description.strip()

        else:
            # # No range, the serial number is the same as the major block
            if details != "":
                sub_dict[key] = details
        # print(key, " ", sub_dict)

        # Sort sub_dict by key ascending
        # Convertir les clés en entiers pour le tri, puis les convertir à nouveau en chaînes
        sorted_sub_dict = {f"{k.split('-')[0]}-{int(k.split('-')[1])}": v for k, v in
                           sorted(sub_dict.items(), key=lambda item: int(item[0].split('-')[1]))}

        build, type_ = separate_manufacturer_and_type(type_info)
        detailed_dict[key] = {'build': build, 'type': type_, 'details': sorted_sub_dict}
        # print(key, detailed_dict[key])

    return detailed_dict


# Découpage fabricant / type d'avion
def separate_manufacturer_and_type(aircraft):
    # Utiliser une expression régulière pour trouver la première occurrence où des lettres suivies par des tirets, des chiffres, ou des combinaisons similaires apparaissent.
    # Cela suppose que le type d'avion commence souvent par un modèle ou un code qui inclut des chiffres ou des tirets.
    match = re.search(r"([\s\S]+?)\s+([A-Z0-9]+[-\s][\s\S]+)", aircraft)
    if match:
        manufacturer = match.group(1).strip()
        aircraft_type = match.group(2).strip()
        return manufacturer, aircraft_type
    else:
        # Retourne l'entrée originale et une chaîne vide si aucune séparation n'est trouvée
        return aircraft, ""


## Affichage des sous-blocs
def display_sub_entries(detailed_dict):
    # Affichage des résultats
    for key, sub_entries in detailed_dict.items():
        print(f"Numéro de série principal: {key}, Build: {sub_entries['build']} Type: {sub_entries['type']}")
        for sub_key, description in sub_entries['details'].items():
            print(f"    Sous-numéro de série: {sub_key}, Description: {description}")
        print("\n")


def nice_print_format(str):
    n = len(str)
    line = "-" * n
    print(f"{line}\n{str}\n{line}")

def parse_delivery_date(dict):
    new_dict = {}
    for key, sub_entries in dict.items():
        for sub_key, description in sub_entries['details'].items():

            # Expression régulière pour les dates dans les formats spécifiés
            date_pattern = r'\b(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{2,4})\b'
            # Diviser le texte en phrases
            sentences = re.split(r'(?<=[.])\s*', description)

            # Prendre les deux premières phrases
            first_two_sentences = '.'.join(sentences[:2])

            # Expression régulière pour trouver les phrases contenant "accepted" ou "delivered"
            keyword_pattern = re.compile(r'\b(?:accepted|delivered|to USAAF|to USAAC)\b', re.IGNORECASE)

            if keyword_pattern.search(first_two_sentences):
                date_matches = re.findall(date_pattern, first_two_sentences, re.IGNORECASE)
                if len(date_matches) > 0:
                    new_dict[sub_key] = date_matches[0]
            else:
                if 'B-17' in sub_entries['type']:
                    match = re.search(date_pattern, description, re.IGNORECASE)
                    if match:
                        # print(sub_key, match.group(0))
                        new_dict[sub_key] = match.group(0)
                else:
                    new_dict[sub_key] = "N/A"


    return new_dict

def filling_missing_serial(dict, first_serial):
    filled_dict = dict.copy()
    prev_serial = first_serial-1

    for key, date in dict.items():
        key_int = int(key.split('-')[1])
        # print("Début boucle for key",key_int, prev_serial)
        if key_int - prev_serial > 1:
            for i in range(prev_serial+1, key_int):
                # print(f"Missing delivery date for serial number 42-{i}, Previous serial: {prev_serial}, Current serial: {key_int}")
                filled_dict[f"{key.split('-')[0]}-{i}"] = "N/A"
            prev_serial = key_int
            continue
        else:
            # print(f"Clé déjà existante: {key} ---- {filled_dict[key]}, Previous serial: {prev_serial}, Current serial: {key_int}")
            prev_serial = key_int
    return filled_dict


if __name__ == "__main__":
    while True:
        ## Récupérer les noms de fichiers disponibles dans /input
        files = [f for f in os.listdir('./input') if f.endswith('.html')]

        ## Trier ces fichiers par ordre ascendant
        files.sort()

        ## Afficher un menu qui va permettre de choisir avec quel fichier on veut travailler
        nice_print_format("Choose a file to extract data from :")
        for i, file in enumerate(files):
            print(f"{i + 1}. {file}")
        choice = int(input("Enter the number of the file you want to work with : "))
        if choice < 1 or choice > len(files):
            nice_print_format("\nInvalid choice. Please try again.")
            continue

        filename = f"./input/{files[choice - 1]}"
        name = Path(filename).stem
        first_serial_number = get_first_serial_number_of_document(filename)
        nice_print_format(f"\nExtracting data from {filename}... Starting with serial number: {first_serial_number}\n")

        main_content = get_html_content(filename)
        # print(main_content)

        data_dict, blocks_number = parse_main_entries(main_content)
        # display_main_entries(data_dict)

        detailed_dict = parse_sub_entries(data_dict)
        # display_sub_entries(detailed_dict)

        delivery_dates = parse_delivery_date(detailed_dict)
        # print(delivery_dates)

        final_delivery = filling_missing_serial(delivery_dates, first_serial_number)
        # print(final_delivery)

        sorted_final_delivery = {f"{k.split('-')[0]}-{int(k.split('-')[1])}": v for k, v in
                           sorted(delivery_dates.items(), key=lambda item: int(item[0].split('-')[1]))}
        # print(sorted_final_delivery)

        final_data = []
        for key,value in sorted_final_delivery.items():
            final_data.append([key, value])
        # print("Final data: ", final_data)

        # Export DataFrame to Excel file
        df = pd.DataFrame(final_data, columns=['Serial Number', 'Delivery Date'])
        name = Path(filename).stem
        print("Nom du fichier: ", name)
        df.to_excel(f"./extracted_delivery/{name}.xlsx", index=False)
        nice_print_format("Extraction completed. Check the extracted_delivery folder for the results.")




