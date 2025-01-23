import bs4
import re
import chardet
import pandas as pd
from pathlib import Path
from call_mistralai_api import callMistralAPI
import time
import os

## Variables globales
blocks_number = 0
time_start = 0
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
    return encoding #"ISO-8859-1"


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


## Découpage fabricant / type d'avion
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


def extract_info_from_description(description):
    prompt = (
        f"Analyze the following aircraft description and provide the last event of its active life in the US military inventory, or what led that aircraft to leave the US inventory."
        f"The mandatory output format is: 'Fate:{{fate}}, End Date:{{date formatted as month/day/year}}, Notes:{{notes}}'."
        f"If there is no information about its active life in the US military, write only 'N/A' in the notes. Notes should be short and only contain words from the initial description."
        f"Same for Fate and End Date, if no information or line empty, put 'N/A' if not present."
        f"No explanation or additional note, don't be talkative and don't repeat the description."
        f"For the fate, classify with only one letter respecting the following criteria and take into account only the last event that led the plane to leave the US Military inventory:"
        f"X for combat loss, shot down, lost, Shot down; lost in action, loss;"
        f"or C for crashed or any of following: wrecked, crash landing, condemned, written off after crash landing, ditched, surveyed;" 
        f"or S for all aircraft sold, privately owned, private ownership, lend-leased or acquired to/by private people, associations or countries that are not major allies of the USA like to CAA, to RFC or to Reconstruction Company;"
        f"or T for all aircraft that have been transferred, diverted to countries like Canada, RAF or UK, Canada or RCAF, Netherlands, France, USSR. For all other countries, like Brazil, Bolivia or non major allies, set it to O, the case for other reason. Same for transfer to US Army Ground Forces or US Navy (USN), this is not a transfer, look for next relevant event;"
        f"or P for all aircraft that have been transferred to Philippines because it was a US holding at this time;"
        f"or Q for all aircraft that ended transformed or used as a trainer, target or CL-26;"
        f"or D stands for decommissioned or any of following: retired, written off, w/o, W/o, withdrawn, wfu, WFU, dismantled, struck off charge, SOC, reclamation, salvaged, reclaimed, scrapped, sent to MASDC;"
        f"or O for any other reasons, no information found after being accepted or still registered, cancelled contract;"
        f"Once again, only the last event should be considered to qualify the fate of the aircraft."
        f"Only letters allowed for fate are X, C, T, P, Q, D, S, O."
        f"Date format to use is US format only. Caution date description can be all linked together, year must have 4 digits."
        f"Don't use any of your own memory, don't browse any website and don't reference any url. Only use the description provided."
        f"Ignore microfilm data mentioned."
        f"Description I want you to analyze is : {description}")

    extracted_info = callMistralAPI(prompt)
    return extracted_info


def extract_info_from_detailed_dict(detailed_dict):
    final_data = []
    prev_serial = first_serial_number - 1 ## Variable pour vérifier si un numéro de série est manquant, doit être initialisé au premier numéro de série du fichier - 1
    counter = 1
    double_counter = 1

    for i, (key, sub_entries) in enumerate(detailed_dict.items()):

        # every step report
        nice_print_format(f"{i + 1} / {blocks_number} major blocks.")
        get_elapsed_time()
        # Loop through sub keys and extract information
        for sub_key, description in sub_entries['details'].items():
            # check counter variable and every 2000 lines, save in a file to avoid loss of data in case of crash
            # print("Compteur : ", counter)
            if counter > 2000 * double_counter:
                dfinter = pd.DataFrame(final_data)
                # Export DataFrame to Excel file
                dfinter.to_excel(f"./extracted_data/{name}-{sub_key}.xlsx", index=False)
                nice_print_format(f"Partial save after {counter} lines extracted")
                double_counter = counter / 2000 + 1


            # print(sub_key.split('-')[1])
            subkey_to_int = int(sub_key.split('-')[1])
            print(sub_key, subkey_to_int, prev_serial)

            # Check serial numbers are missing / add missing serial numbers
            if  subkey_to_int > prev_serial + 1:
                for i in range(prev_serial + 1, subkey_to_int):
                    sub_key_to_add = f"{sub_key.split('-')[0]}-{i}"
                    print('Adding serial Number : ', sub_key_to_add, "Sub_key : ", sub_key, "prev_serial", prev_serial)
                    final_data.append({
                        'Serial Number': sub_key_to_add,
                        'Build': sub_entries['build'],
                        'Type': sub_entries['type'],
                        'Fate': "Z",
                        'End Date': "1/1/99",
                        'Notes': "Serial number not found in file"
                    })
                    counter += 1

            try:
                extracted_info = extract_info_from_description(description)
                if extracted_info:
                    extracted_info = extracted_info.replace("\n", " ")
                # print(extracted_info)
                print('Serial Number : ', sub_key, ', Build : ', sub_entries['build'], '  , Type : ',
                      sub_entries['type'], "    ", extracted_info)

                if "End Date:" in extracted_info:
                    final_date = "".join(extracted_info.split(', ')[1].split(': ')[1:])
                    date = f"{final_date}"
                else:
                    date = "No information found"
                if "Fate:" in extracted_info:
                    fate = extracted_info.split(', ')[0].split(':')[1].strip()
                else:
                    fate = "No information found"
                if "Notes:" in extracted_info:
                    notes = extracted_info.split('Notes:')[1].strip()
                else:
                    notes = "No information found"
                final_data.append({
                    'Serial Number': sub_key,
                    'Build': sub_entries['build'],
                    'Type': sub_entries['type'],
                    'Fate': fate,
                    'End Date': date,
                    'Notes': notes
                })
            except TypeError:
                final_data.append({
                    'Serial Number': sub_key,
                    'Build': sub_entries['build'],
                    'Type': sub_entries['type'],
                    'Fate': "Unable to extract information",
                    'End Date': "Unable to extract information",
                    'Notes': "Unable to extract information"
                })
            prev_serial = subkey_to_int
            counter += 1

            # print(final_data)
    return final_data

def nice_print_format(str):
    n = len(str)
    line = "-" * n
    print(f"{line}\n{str}\n{line}")


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

        time_start = time.time()


        main_content = get_html_content(filename)
        # print(main_content)

        data_dict, blocks_number = parse_main_entries(main_content)
        # display_main_entries(data_dict)

        detailed_dict = parse_sub_entries(data_dict)
        # display_sub_entries(detailed_dict)
        # print(detailed_dict["44-70255/70554"])

        nice_print_format(f"{blocks_number} major blocks to process.")

        # # # Extract information from detailed dictionary
        final_data = extract_info_from_detailed_dict(detailed_dict)

        # Convert to Excel file, re calculate/check fate and format column
        # Create a DataFrame from the final data
        df = pd.DataFrame(final_data)

        # Export DataFrame to Excel file
        name = Path(filename).stem
        df.to_excel(f"./extracted_data/{name}.xlsx", index=False)
        nice_print_format("Extraction completed. Check the extracted_data folder for the results.")
        get_elapsed_time()




