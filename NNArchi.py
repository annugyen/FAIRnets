import json
import re
from urllib import request

import pandas as pd

keras_apps_list = ['Xception',
                   'VGG16',
                   'VGG19',
                   'ResNet50',
                   'ResNet101',
                   'ResNet152',
                   'ResNet50V2',
                   'ResNet101V2',
                   'ResNet152V2',
                   'InceptionV3',
                   'InceptionResNetV2',
                   'MobileNet',
                   'MobileNetV2',
                   'DenseNet121',
                   'DenseNet169',
                   'DenseNet201',
                   'NASNetMobile',
                   'NASNetLarge']

def get_repo_full_name(repo_url):
    name_pattern = re.compile('github.com/', re.I)
    name_search = name_pattern.search(repo_url)
    repo_full_name = repo_url[name_search.end():]
    return repo_full_name

def split_py(py_file):

    #delete notes using """
    while re.search('(\"\"\")(.*?)(\"\"\")', py_file):
        py_file = re.sub('(\"\"\")([\s\S]*?)(\"\"\")', '', py_file)
    
    code_split = py_file.split('\n')
    line_num = len(code_split)
    py_in_lines = {}
    for i, line in enumerate(code_split):
        space_num = 0
        is_code = True
        space_search = re.search('[^\s]', line)
        if space_search:
            space_num = space_search.span()[0]
            if line[space_num] == '#':
                is_code = False
        else:
            is_code = False
        py_in_lines[i] = (line, space_num, is_code)
    return py_in_lines, line_num

def extract_layer_info(add_info):
    extracted_layer_info = {}
    search_type = re.search('\(', add_info)
    layer_type = add_info[:search_type.span()[0]]
    extract_layer_info['type'] = layer_type
    #todo: classify different layer type
    return extracted_layer_info

def extract_architecture_from_python(repo_full_name):

    def get_add_info(py_in_lines, quote_start):
        quote_num = 1
        quote_line = quote_start[0]
        quote_postion = quote_start[1]
        while True:
            if quote_postion < len(py_in_lines[quote_line][0]):
                if py_in_lines[quote_line][0][quote_postion] == '(':
                    quote_num += 1
                elif py_in_lines[quote_line][0][quote_postion] == ')':
                    quote_num -= 1
            if quote_num == 0:
                break
            quote_postion += 1
            if quote_postion >= len(py_in_lines[quote_line][0]):
                quote_postion = 0
                quote_line += 1
            add_info = py_in_lines[quote_start[0]][0][quote_start[1]:]
            for i in range(quote_start[0] + 1, quote_line):
                add_info += py_in_lines[i][0][py_in_lines[i][1]:]
            add_info += py_in_lines[quote_line][0][py_in_lines[quote_line][1]:quote_postion]
        return add_info

    search_terms = ['"import+keras"', '"from+keras"', 'keras.models', 'keras.layers', 'keras.utils', 'tf.keras.models.Sequential()']
    query_search_terms = '+OR+'.join(search_terms)
    search_url = 'https://api.github.com/search/code?limit=100&per_page=100&q=' + query_search_terms + '+in:file+extension:py+repo:' + repo_full_name
    response = request.urlopen(search_url)
    html = response.read()
    json_data = json.loads(html.decode("utf-8"))

    py_files_list = []
    if 'items' in json_data:
        for file in json_data['items']:
            raw_url = file['html_url'].replace('github.com', 'raw.githubusercontent.com').replace('blob/', '')
            py_files_list.append(raw_url)
    else:
        print('Keras may not be used.')
    
    for raw_file_url in py_files_list:
        raw_file = request.urlopen(raw_file_url).read().decode("utf-8")
        
        libs_set = set()
        lib_search = re.finditer('^(from|import)\s(\w+)', raw_file, re.MULTILINE)
        if lib_search:
            for lib in lib_search:
                libs_set.add(lib.group(2))

        model_num = 0
        model_detail = {}
        
        if ('keras' in libs_set) or ('Keras' in libs_set):
            py_in_lines, line_num = split_py(raw_file)
            for line_index in range(line_num):
                search_seq = re.search('Sequential\(', py_in_lines[line_index][0])
                search_apps = re.search('applications\.', py_in_lines[line_index][0])
                if search_seq:
                    model_num += 1
                    model_detail[model_num] = {}
                    model_detail[model_num]['type'] = 'Sequential' 
                    '''
                    next_line = line_index
                    while True:
                        next_line += 1
                        if py_in_lines[next_line][2]:
                            if py_in_lines[next_line][1] >= py_in_lines[line_index][1]:
                                search_add = re.search('\.add\(', py_in_lines[next_line][0])
                                if search_add:
                                    quote_start = (next_line, search_add.span()[1])
                                    add_info = get_add_info(py_in_lines, quote_start)
                                    layers[layer_index] = extract_layer_info(add_info)
                            else:
                                break
                        else:
                            continue
                    '''
                elif search_apps:
                    model_num += 1
                    model_detail[model_num] = {}
                    temp_line = py_in_lines[line_index][0]
                    app_type_start = search_apps.span()[1]
                    app_type = temp_line[app_name_start:app_name_start + re.search('\(', temp_line[app_name_start:]).span()[0]]
                    if app_type in keras_apps_list:
                        model_detail[model_num]['type'] = app_type
                    else:
                        model_detail[model_num]['type'] = 'Unknown base model: ' + app_type
                next_line = line_index
                layer_index = 0
                layers = {}
                while True:
                    next_line += 1
                    if py_in_lines[next_line][2]:
                        if py_in_lines[next_line][1] >= py_in_lines[line_index][1]:
                            search_add = re.search('\.add\(', py_in_lines[next_line][0])
                            if search_add:
                                layer_index += 1
                                quote_start = (next_line, search_add.span()[1])
                                add_info = get_add_info(py_in_lines, quote_start)
                                layers[layer_index] = extract_layer_info(add_info)
                            search_compile = re.search('\.compile\(', py_in_lines[next_line][0])
                            if search_compile:
                                #todo search optimizer and loss function
                                pass
                        else:
                            break
                    else:
                        continue
                model_detail[model_num]['layers'] = layers
                #todo: add optimizer and loss function

'''
#main
if __name__ == '__main__':
    data_path = './files.json'
    with open(data_path, 'r') as file:
        data = json.load(file)
    file.close()
    df = pd.DataFrame(data)
    repo_url_dict = data['repo_url']
    for repo in repo_url_dict:
        repo_url = repo_url_dict[repo]
        repo_full_name = get_repo_full_name(repo_url)
'''
#test
repo_full_name = 'francarranza/genre_classification'
extract_architecture_from_python(repo_full_name)