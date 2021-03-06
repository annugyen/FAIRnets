import json
import random
import re
import time
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
    name_pattern = re.compile('github\.com/', re.I)
    name_search = name_pattern.search(repo_url)
    repo_full_name = repo_url[name_search.end():]
    return repo_full_name

def split_py(py_file):
    '''
    Split .py file into lines and information of each line(number of space at beginning and if this line is a valid code).
    Delete notes using #, " and ' at same time.
    '''

    #delete notes using """
    while re.search('(\"\"\")([\s\S]*?)(\"\"\")', py_file):
        py_file = re.sub('(\"\"\")([\s\S]*?)(\"\"\")', '', py_file)
    
    #delete notes using '''
    while re.search('(\'\'\')([\s\S]*?)(\'\'\')', py_file):
        py_file = re.sub('(\'\'\')([\s\S]*?)(\'\'\')', '', py_file)
    
    code_split = py_file.split('\n')
    line_num = len(code_split)
    py_in_lines = {}
    for i, line in enumerate(code_split):
        space_num = 0
        is_code = True
        space_search = re.search('\S', line)
        if space_search:
            space_num = space_search.span()[0]
            if line[space_num] == '#':
                is_code = False
                line = ''
                space_num = 0
        else:
            is_code = False
        py_in_lines[i] = (line, space_num, is_code)
    return py_in_lines, line_num

def extract_layer_info(quote_info):
    '''
    Extract information of different layers.
    '''
    extracted_layer_info = {}
    search_type = re.search('\(', quote_info)
    if search_type:
        layer_type = quote_info[:search_type.span()[0]]
    else:
        layer_type = quote_info
    
    #todo: classify different layer type
    
    if layer_type == 'Dense':
        layer_shape = quote_info[search_type.span()[1]:re.search('\)|,', quote_info).span()[0]]
        
        search_activation = re.search('activation=', quote_info)
        layer_activation = 'linear'
        if search_activation:
            layer_activation_start = search_activation.span()[1]
            search_comma = re.search(',', quote_info[layer_activation_start:])
            if search_comma:
                layer_activation = quote_info[layer_activation_start:layer_activation_start + search_comma.span()[0]]
            else:
                layer_activation = quote_info[layer_activation_start:-1]
            layer_activation = re.sub('\'', '', layer_activation)
            if layer_activation.lower() == 'none':
                layer_activation = 'linear'
        extracted_layer_info = {'type':layer_type, 'shape':layer_shape, 'activation':layer_activation, 'info':quote_info}
    
    elif layer_type in ['Dropout', 'SpatialDropout1D', 'SpatialDropout2D', 'SpatialDropout3D']:
        search_rate = re.search('rate=', quote_info)
        if search_rate:
            layer_rate = quote_info[search_rate.span()[1]:re.search('\)|,', quote_info).span()[0]]
        else:
            layer_rate = quote_info[re.search('\(', quote_info).span()[1]:re.search('\)|,', quote_info).span()[0]]
        extracted_layer_info = {'type':layer_type, 'rate':layer_rate, 'info':quote_info}
    
    elif layer_type == 'Flatten':
        layer_shape = 'Same with former layer'
        extracted_layer_info = {'type':layer_type, 'shape':layer_shape, 'info':quote_info}
    
    elif layer_type in ['Conv1D', 'Conv2D', 'SeparableConv1D', 'SeparableConv2D']: #todo add conv3d
        search_filters = re.search('filters=', quote_info)
        layer_filters = 'Unknown'
        if search_filters:
            layer_filters_start = search_filters.span()[1]
            search_comma = re.search(',', quote_info[layer_filters_start:])
            if search_comma:
                layer_filters = quote_info[layer_filters_start:layer_filters_start + search_comma.span()[0]]
            else:
                layer_filters = quote_info[layer_filters_start:-1]
        
        search_kernel_size = re.search('kernel_size=', quote_info)
        layer_kernel_size = 'Unknown'
        if search_kernel_size:
            layer_kernel_size_start = search_kernel_size.span()[1]
            search_comma = re.search(',', quote_info[layer_kernel_size_start:])
            if search_comma:
                layer_kernel_size = quote_info[layer_kernel_size_start:layer_kernel_size_start + search_comma.span()[0]]
            else:
                layer_kernel_size = quote_info[layer_kernel_size_start:-1]
        
        search_strides = re.search('strides=', quote_info)
        if layer_type[-2:] =='2D':
            layer_strides = '(1, 1)'
        else:
            layer_strides = '1'
        if search_strides:
            layer_strides_start = search_strides.span()[1]
            search_comma = re.search(',', quote_info[layer_strides_start:])
            if search_comma:
                layer_strides = quote_info[layer_strides_start:layer_strides_start + search_comma.span()[0]]
            else:
                layer_strides = quote_info[layer_strides_start:-1]
        
        search_padding = re.search('padding=', quote_info)
        layer_padding = 'valid'
        if search_padding:
            search_causal = re.search('causal', quote_info)
            search_same = re.search('same', quote_info)
            if search_causal:
                layer_padding = 'causal'
            elif search_same:
                layer_padding = 'same'
        
        search_activation = re.search('activation=', quote_info)
        layer_activation = 'linear'
        if search_activation:
            layer_activation_start = search_activation.span()[1]
            search_comma = re.search(',', quote_info[layer_activation_start:])
            if search_comma:
                layer_activation = quote_info[layer_activation_start:layer_activation_start + search_comma.span()[0]]
            else:
                layer_activation = quote_info[layer_activation_start:-1]
            layer_activation = re.sub('\'', '', layer_activation)
            if layer_activation.lower() == 'none':
                layer_activation = 'linear'
        extracted_layer_info = {'type':layer_type, 'filters':layer_filters, 'kernel_size':layer_kernel_size, 'strides':layer_strides, 'padding':layer_padding, 'activation':layer_activation, 'info':quote_info}
    
    elif layer_type in ['MaxPooling1D', 'MaxPooling2D', 'MaxPooling3D', 'AveragePooling1D', 'AveragePooling2D', 'AveragePooling3D']: #todo add other pooling
        search_pool_size = re.search('pool_size=', quote_info)
        if layer_type[-2:] == '3D':
            layer_pool_size = '(2, 2, 2)'
        elif layer_type[-2:] == '2D':
            layer_pool_size = '(2, 2)'
        else:
            layer_pool_size = '2'
        if search_pool_size:
            layer_pool_size_start = search_pool_size.span()[1]
            search_comma = re.search(',', quote_info[layer_pool_size_start:])
            if search_comma:
                layer_pool_size = quote_info[layer_pool_size_start:layer_pool_size_start + search_comma.span()[0]]
            else:
                layer_pool_size = quote_info[layer_pool_size_start:-1]
        
        search_strides = re.search('strides=', quote_info)
        layer_strides = layer_pool_size
        if search_strides:
            layer_strides_start = search_strides.span()[1]
            search_comma = re.search(',', quote_info[layer_strides_start:])
            if search_comma:
                layer_strides = quote_info[layer_strides_start:layer_strides_start + search_comma.span()[0]]
            else:
                layer_strides = quote_info[layer_strides_start:-1]
            if layer_strides.lower() == 'none':
                layer_strides = layer_pool_size
        
        search_padding = re.search('padding=', quote_info)
        layer_padding = 'valid'
        if search_padding:
            search_causal = re.search('causal', quote_info)
            search_same = re.search('same', quote_info)
            if search_causal:
                layer_padding = 'causal'
            elif search_same:
                layer_padding = 'same'
        extracted_layer_info = {'type':layer_type, 'pool_size':layer_pool_size, 'strides':layer_strides, 'padding':layer_padding, 'info':quote_info}
    else:
        extracted_layer_info = {'type':layer_type, 'info':quote_info}
    return extracted_layer_info

def extract_compile_info(quote_info):
    '''
    Extract information of loss, optimizer and metrics
    '''

    loss, optimizer, metrics = 'None', 'None', 'None'
    search_loss = re.search('loss=', quote_info)
    if search_loss:
        loss_start = search_loss.span()[1]
        search_comma = re.search(',', quote_info[loss_start:])
        if search_comma:
            loss = quote_info[loss_start:loss_start + search_comma.span()[0]]
        else:
            loss = quote_info[loss_start:-1]
        loss = re.sub('\'', '', loss)

    search_optimizer = re.search('optimizer=', quote_info)
    if search_optimizer:
        optimizer_start = search_optimizer.span()[1]
        search_comma = re.search(',', quote_info[optimizer_start:])
        if search_comma:
            optimizer = quote_info[optimizer_start:optimizer_start + search_comma.span()[0]]
        else:
            optimizer = quote_info[optimizer_start:-1]
        optimizer = re.sub('\'', '', optimizer)

    search_metrics = re.search('metrics=', quote_info)
    if search_metrics:
        metrics_start = search_metrics.span()[1]
        metrics_end = metrics_start + 1
        if quote_info[metrics_start] == '[':
            if_metrics_end = 1
            while if_metrics_end != 0:
                if quote_info[metrics_end] == '[':
                    if_metrics_end += 1
                elif quote_info[metrics_end] == ']':
                    if_metrics_end -= 1
                metrics_end += 1
        elif quote_info[metrics_start] == '{':
            if_metrics_end = 1
            while if_metrics_end != 0:
                if quote_info[metrics_end] == '{':
                    if_metrics_end += 1
                elif quote_info[metrics_end] == '}':
                    if_metrics_end -= 1
                metrics_end += 1
        metrics = quote_info[metrics_start:metrics_end]
    return loss, optimizer, metrics

def extract_architecture_from_python(repo_full_name):
    '''
    Extract architecture of NNs from .py file in a repo.
    '''

    Token_list = ['1498e12f29400f246eb5b2cf1c6ccfb1a4970c4a',
                  'f24e286bab8a40e1995c1f1dcacd6e31e6816ac1',
                  'd10d26ffe911ab0d569b5ddc5c777f26b9ef057a',
                  '66b9970c6a9d24d61e167cda2f3997219bae3447']

    def get_quote_info(py_in_lines, quote_start):
        '''
        Get information in quotes, including multiple lines.
        '''

        quote_num = 1
        quote_line = quote_start[0]
        quote_postion = quote_start[1]
        #while True:
        while quote_num != 0:
            if quote_postion < len(py_in_lines[quote_line][0]):
                if py_in_lines[quote_line][0][quote_postion] == '(':
                    quote_num += 1
                elif py_in_lines[quote_line][0][quote_postion] == ')':
                    quote_num -= 1
            if quote_num != 0:
                quote_postion += 1
                if quote_postion >= len(py_in_lines[quote_line][0]):
                    quote_postion = 0
                    quote_line += 1
        if quote_start[0] == quote_line:
            quote_info = py_in_lines[quote_start[0]][0][quote_start[1]:quote_postion]
        else:
            quote_info = py_in_lines[quote_start[0]][0][quote_start[1]:]
            for i in range(quote_start[0] + 1, quote_line):
                quote_info += py_in_lines[i][0][py_in_lines[i][1]:]
            quote_info += py_in_lines[quote_line][0][py_in_lines[quote_line][1]:quote_postion]
        quote_info = re.sub(' ', '', quote_info)
        return quote_info
    
    #'''
    search_terms = ['"import+keras"', '"from+keras"', 'keras.models', 'keras.layers', 'keras.utils', 'tf.keras.models.Sequential()']
    query_search_terms = '+OR+'.join(search_terms)
    search_url = 'https://api.github.com/search/code?limit=100&per_page=100&q=' + query_search_terms + '+in:file+extension:py+repo:' + repo_full_name
    #Token_1 = '1498e12f29400f246eb5b2cf1c6ccfb1a4970c4a'
    Token_idx = random.randint(0,len(Token_list) - 1)
    headers_1 = {'Authorization':'token ' + Token_list[Token_idx]}
    url_request = request.Request(search_url, headers = headers_1)
    response = request.urlopen(url_request)
    html = response.read()
    json_data = json.loads(html.decode("utf-8"))

    py_files_list = []
    if 'items' in json_data:
        for file in json_data['items']:
            raw_url = file['html_url'].replace('github.com', 'raw.githubusercontent.com').replace('blob/', '')
            py_files_list.append(raw_url)
    else:
        print('Keras may not be used.')
    #'''
    
    ''' for maunal test
    #py_files_list = ["https://raw.githubusercontent.com/jw15/wildflower-finder/master/src/cnn_resnet50.py"] #test file
    #py_files_list = ["https://raw.githubusercontent.com/francarranza/genre_classification/master/train.py"] #test file
    py_files_list = ["https://raw.githubusercontent.com/nagyben/CarND-Behavioral-Cloning-P3/f044a3a1eff5b30171b763eb2eda0b2dba19469e/train.py"] #test file
    '''
    
    model_num = 0
    model_detail = {}

    for raw_file_url in py_files_list:
        #Token_2 = 'f24e286bab8a40e1995c1f1dcacd6e31e6816ac1'
        Token_idx = random.randint(0,len(Token_list) - 1)
        headers_2 = {'Authorization':'token ' + Token_list[Token_idx]}
        raw_file_request = request.Request(raw_file_url, headers = headers_2)
        raw_file = request.urlopen(raw_file_request).read().decode("utf-8")
        
        libs_set = set()
        lib_search = re.finditer('^(from|import)\s(\w+)', raw_file, re.MULTILINE)
        if lib_search:
            for lib in lib_search:
                libs_set.add(lib.group(2))
        
        if ('keras' in libs_set) or ('Keras' in libs_set):
            py_in_lines, line_num = split_py(raw_file)
            line_index = 0
            model_start_index = 0
            while line_index < line_num:
                search_seq = re.search('Sequential\(', py_in_lines[line_index][0])
                search_apps = re.search('applications\.(.*?)\(', py_in_lines[line_index][0])
                model_found = False

                if py_in_lines[line_index][2]:
                    if search_apps:
                        #temp_line = py_in_lines[line_index][0]
                        #app_type_start = search_apps.span()[1]
                        app_type = search_apps.group(1)
                        if app_type in keras_apps_list:
                            model_num += 1
                            model_detail[model_num] = {}
                            model_found = True
                            model_detail[model_num]['type'] = app_type
                            model_start_index = line_index
                        #else: #todo this case should be further considerd
                            #model_detail[model_num]['type'] = 'Unknown base model: ' + app_type
                    elif search_seq:
                        model_start_index = line_index
                        model_num += 1
                        model_detail[model_num] = {}
                        model_detail[model_num]['type'] = 'Sequential'
                        model_found = True
                
                model_end_index = model_start_index
                while model_found:
                    if py_in_lines[model_end_index][2] and py_in_lines[model_end_index][1] < py_in_lines[model_start_index][1]:
                        break
                    elif model_end_index < line_num - 1:
                        model_end_index += 1
                    else:
                        break
                
                if model_found:
                    layer_index = 0
                    layers = {}
                    model_loss, model_optimizer, model_metrics = 'None', 'None', 'None'
                    for idx in range(model_start_index + 1, model_end_index + 1):
                        search_add = re.search('\.add\(', py_in_lines[idx][0])
                        search_compile = re.search('\.compile\(', py_in_lines[idx][0])
                        if py_in_lines[idx][2]:
                            if search_add:
                                layer_index += 1
                                quote_start = (idx, search_add.span()[1])
                                quote_info = get_quote_info(py_in_lines, quote_start)
                                layers[layer_index] = extract_layer_info(quote_info)
                            elif search_compile:
                                quote_start = (idx, search_compile.span()[1])
                                quote_info = get_quote_info(py_in_lines, quote_start)
                                model_loss, model_optimizer, model_metrics = extract_compile_info(quote_info)
                                break
                    model_detail[model_num]['layers'] = layers
                    model_detail[model_num]['loss'] = model_loss
                    model_detail[model_num]['optimizer'] = model_optimizer
                    model_detail[model_num]['metrics'] = model_metrics
                    line_index = model_end_index + 1
                else:
                    line_index += 1
    
    return model_detail

#'''
#main
if __name__ == '__main__':
    data_path = './files.json'
    with open(data_path, 'r') as file:
        data = json.load(file)
    file.close()
    df = pd.DataFrame(data)
    repo_url_dict = data['repo_url']
    for idx, repo in enumerate(repo_url_dict):
        repo_url = repo_url_dict[repo]
        repo_full_name = get_repo_full_name(repo_url)
        model_detail = extract_architecture_from_python(repo_full_name)
        print('%d: finish' % idx)
        time.sleep(1)

#'''
'''
#test
repo_full_name = 'francarranza/genre_classification'
extract_architecture_from_python(repo_full_name)
'''
