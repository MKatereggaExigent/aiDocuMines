#!/usr/bin/env python3
import os
import ast

project_root = os.getcwd()
excluded_dirs = {'venv', '.venv', 'vmEnv312', '__pycache__', 'site-packages'}

def is_model_class(node):
    return isinstance(node, ast.ClassDef) and any(
        isinstance(base, ast.Attribute) and base.attr == 'Model' or
        isinstance(base, ast.Name) and base.id == 'Model'
        for base in node.bases
    )

def parse_fields(node):
    fields = []
    for stmt in node.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            field_type = getattr(stmt.value.func, 'attr', None)
            if field_type:
                field_name = stmt.targets[0].id
                fields.append((field_name, field_type))
    return fields

def scan_models_py(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    models = []
    for node in tree.body:
        if is_model_class(node):
            model_name = node.name
            fields = parse_fields(node)
            models.append((model_name, fields))
    return models

for root, dirs, files in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in excluded_dirs]
    for file in files:
        if file == "models.py":
            path = os.path.join(root, file)
            print(f"\n📦 File: {path}")
            models = scan_models_py(path)
            for model_name, fields in models:
                print(f"\n  🧱 Model: {model_name}")
                for name, field_type in fields:
                    print(f"    - {name}: {field_type}")

