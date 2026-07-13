import json
import re
from pathlib import Path

UE_BASE = r"C:\work\unreal\UnrealEngine-release"
ENGINE_PUBLIC = rf"{UE_BASE}\Engine\Source\Runtime\Engine\Public\Materials"

CLASSES = {
    "DotProduct": "MaterialExpressionDotProduct.h",
    "CrossProduct": "MaterialExpressionCrossProduct.h",
    "Normalize": "MaterialExpressionNormalize.h",
    "ComponentMask": "MaterialExpressionComponentMask.h",
    "AppendVector": "MaterialExpressionAppendVector.h",
    "Distance": "MaterialExpressionDistance.h",
    "Length": "MaterialExpressionLength.h",
    "Desaturation": "MaterialExpressionDesaturation.h",
    "Fresnel": "MaterialExpressionFresnel.h",
    "SphereMask": "MaterialExpressionSphereMask.h",
    "RotateAboutAxis": "MaterialExpressionRotateAboutAxis.h",
    "DeriveNormalZ": "MaterialExpressionDeriveNormalZ.h",
    "Transform": "MaterialExpressionTransform.h",
    "TransformPosition": "MaterialExpressionTransformPosition.h",
}

def read_file(path):
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        return f.read()

def extract_default_from_tooltip(text):
    match = re.search(r"Defaults to ['\"]?(\w+)['\"]?", text)
    if match:
        prop_name = match.group(1)
        if prop_name in ['Pixel', 'World', 'Normal', 'Camera']:
            return None
        return prop_name
    return None

def extract_properties(header_content):
    inputs = []
    pattern = r'UPROPERTY\((.*?)\)\s*FExpressionInput\s+(\w+);'
    
    for match in re.finditer(pattern, header_content, re.DOTALL):
        meta = match.group(1)
        prop_name = match.group(2)
        
        required = not ('RequiredInput = "false"' in meta or 'RequiredInput=false' in meta)
        default_prop = None
        
        override_match = re.search(r'OverridingInputProperty\s*=\s*"(\w+)"', meta)
        if override_match:
            default_prop = override_match.group(1)
        else:
            tooltip_match = re.search(r'ToolTip\s*=\s*"([^"]*)"', meta)
            if tooltip_match:
                default_prop = extract_default_from_tooltip(tooltip_match.group(1))
        
        inputs.append({
            'name': prop_name,
            'prop': prop_name,
            'required': required,
            'default_prop': default_prop
        })
    
    return inputs

def extract_prop_pins(header_content):
    prop_pins = []
    lines = header_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'ShowAsInputPin' in line:
            uprop_text = ''
            j = i
            paren_depth = 0
            while j < len(lines):
                uprop_text += lines[j] + '\n'
                paren_depth += lines[j].count('(') - lines[j].count(')')
                if paren_depth == 0 and ')' in lines[j]:
                    if j + 1 < len(lines):
                        prop_line = lines[j + 1]
                        prop_line = prop_line.strip()
                        
                        kind_match = re.search(r'ShowAsInputPin\s*=\s*"(Primary|Advanced)"', uprop_text)
                        if kind_match:
                            kind = kind_match.group(1)
                            
                            prop_match = re.match(r'([\w<>,:\s]+?)\s+(\w+)\s*(?:[:=]|;)', prop_line)
                            if prop_match:
                                prop_type = prop_match.group(1).strip()
                                prop_name = prop_match.group(2)
                                
                                prop_type = prop_type.replace('TEnumAsByte<enum ', 'enum:').replace('>', '')
                                
                                prop_pins.append({
                                    'name': prop_name,
                                    'prop': prop_name,
                                    'kind': kind,
                                    'type': prop_type
                                })
                    break
                j += 1
        i += 1
    
    return prop_pins

def extract_editable_properties(header_content):
    props = {}
    pattern = r'UPROPERTY\((.*?Edit(?:Anywhere|DefaultsOnly).*?)\)\s*([\w<>,:\s]+?)\s+(\w+)(?:\s*[:=]\s*([^;]+))?;'
    
    for match in re.finditer(pattern, header_content, re.DOTALL):
        meta = match.group(1)
        prop_type = match.group(2).strip()
        prop_name = match.group(3)
        default_val = match.group(4)
        
        if 'ShowAsInputPin' in meta:
            continue
        
        if re.search(r':\d+$', prop_type):
            continue
        
        type_str = prop_type.replace('TEnumAsByte<enum ', 'enum:').replace('>', '')
        
        default_parsed = None
        if default_val:
            default_val = default_val.strip()
            try:
                if default_val.endswith('f'):
                    default_parsed = float(default_val[:-1])
                elif default_val.isdigit():
                    default_parsed = int(default_val)
                else:
                    default_parsed = default_val
            except:
                default_parsed = default_val
        
        props[prop_name] = {'type': type_str, 'default': default_parsed}
    
    return props

DESCRIPTIONS = {
    "DotProduct": "2つのベクトルの内積を計算",
    "CrossProduct": "2つのベクトルの外積を計算",
    "Normalize": "ベクトルを正規化(単位ベクトル化)",
    "ComponentMask": "ベクトルの特定のコンポーネント(R/G/B/A)を選択出力",
    "AppendVector": "2つのベクトル・スカラーを結合して高次元ベクトルを作成",
    "Distance": "2点間の距離を計算",
    "Length": "ベクトルの長さ・大きさを計算",
    "Desaturation": "色を彩度を下げて灰色化(グレースケール変換)",
    "Fresnel": "フレネル効果を計算、視点角度による鏡面反射率を算出",
    "SphereMask": "球体との距離に基づいてマスク値を生成",
    "RotateAboutAxis": "任意の軸周りにベクトルを回転",
    "DeriveNormalZ": "法線XY成分からZ成分を復元(法線圧縮用)",
    "Transform": "ベクトルをある座標系から別の座標系に変換",
    "TransformPosition": "位置座標をある座標系から別の座標系に変換",
}

def extract_class_info(class_name, header_file):
    header_path = Path(ENGINE_PUBLIC) / header_file
    if not header_path.exists():
        print(f"  ERROR: {header_path} not found")
        return None
    
    content = read_file(str(header_path))
    
    return {
        'class': f"/Script/Engine.UMaterialExpression{class_name}",
        'header': f"Materials/{header_file}",
        'desc': DESCRIPTIONS.get(class_name, ""),
        'inputs': extract_properties(content),
        'prop_pins': extract_prop_pins(content),
        'outputs': [{'name': ''}],
        'props': extract_editable_properties(content),
        'notes': '',
        'verified': False
    }

output = {}
for class_name, header_file in CLASSES.items():
    print(f"Processing {class_name}...")
    info = extract_class_info(class_name, header_file)
    if info:
        output[class_name] = info

output_dir = Path(r"C:\work\script\ue_material_skill\catalog\generated")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "C04.json"

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(output)} classes to {output_file}")
