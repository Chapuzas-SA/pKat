# basicos
import os
import sys
# Kaitai
import kaitaistruct
# Dyn' imports y argumentos
import importlib
import argparse
# Formatos
import json
import xml.etree.ElementTree as ET
try:
    import yaml   # pip install pyyaml
except ImportError:
    yaml = None

def obj_to_dict(obj):
    import numbers
    if isinstance(obj, (bool, numbers.Number)) or obj is None:
        return obj
    elif isinstance(obj, bytes):
        return ' '.join(f'{b:02X}' for b in obj)
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, list):
        return [obj_to_dict(x) for x in obj]
    else:
        root = {}
        for attr in dir(obj):
            if attr.startswith('_'):
                continue
            try:
                val = getattr(obj, attr)
            except Exception:
                continue
            if callable(val):
                continue
            v = obj_to_dict(val)
            if v is not None:
                root[attr] = v
        if not root:
            return f'OPAQUE ({type(obj).__name__})'
        return root

def dict_to_xml(tag, d):
    elem = ET.Element(tag)

    if isinstance(d, dict):
        for key, val in d.items():
            child = dict_to_xml(key, val)
            elem.append(child)

    elif isinstance(d, list):
        for item in d:
            child = dict_to_xml("item", item)
            elem.append(child)

    else:
        if isinstance(d, bool):
            elem.set("type", "bool")
        elif isinstance(d, int):
            elem.set("type", "int")
        elif isinstance(d, float):
            elem.set("type", "float")
        elif isinstance(d, (bytes, str)) and " " in str(d):
            elem.set("type", "bytes")
        else:
            elem.set("type", type(d).__name__)

        elem.text = str(d)

    return elem

def to_output(data, formato="json"):
    formato = formato.lower()
    if formato == "json":
        return json.dumps(data, ensure_ascii=False)
    elif formato == "yaml":
        if yaml is None:
            raise RuntimeError("PyYAML no está instalado (pip install pyyaml)")
        return yaml.dump(data, sort_keys=False, allow_unicode=True)
    elif formato == "xml":
        root = dict_to_xml("root", data)
        return ET.tostring(root, encoding="unicode")
    else:
        raise ValueError(f"Formato de salida no soportado: {formato}")

def load_parsers(base_pkg='formats'):
    parsers = {}
    base_path = os.path.join(os.path.dirname(__file__), base_pkg)    
    for root, dirs, files in os.walk(base_path):
        if 'utils' in dirs:
            dirs.remove('utils')
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(__file__))
                mod_path = rel_path[:-3].replace(os.path.sep, '.')
                module = importlib.import_module(mod_path)
                class_name = file[:-3].replace('_', ' ').title().replace(' ', '')
                if hasattr(module, class_name):
                    parsers[file[:-3]] = getattr(module, class_name)
    return parsers

def main():
    parser = argparse.ArgumentParser(description="Parser de ficheros con Kaitai Struct")

    parser.add_argument("-i", "--input-format", help="Formato origen del archivo a analizar (ej: zip, jpeg, elf, etc.)")
    parser.add_argument("-l", "--list-input-formats", action="store_true", help="Obtener listado de formatos de entrada soportados")
    parser.add_argument("-o", "--output-format", choices=["json", "yaml", "xml"], default="json", help="Formato de salida a utilizar (por defecto: JSON)")
    parser.add_argument("-f", "--file", help="Ruta del archivo a analizar")
    args = parser.parse_args()

    parsers = load_parsers()

    if args.list_input_formats:
        print(f"Formatos soportados:")
        for f in parsers.keys():
            print(f"- {f}")
        sys.exit(1)
    else:
        if not args.input_format or not args.file:
            print("Debes indicar --input-format y --file (o usa --list-input-formats)")
            sys.exit(1)

    try:
        parser_cls = parsers[args.input_format]
        parsed = parser_cls.from_file(args.file)
        output = obj_to_dict(parsed)
        print(to_output(output, args.output_format))
    except kaitaistruct.ValidationNotEqualError:
        print(f"El archivo no coincide con el formato esperado ({args.input_format})")

    except ValueError as ve:
        print(f"Error en parámetros: {ve}")

    except Exception as e:
        print(f"Error al tratar el formato ({args.input_format}):")

if __name__ == "__main__":
    main()
