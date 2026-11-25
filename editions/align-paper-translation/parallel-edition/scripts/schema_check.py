"""Small offline fallback for common JSON Schema assertions; report unsupported keywords."""
import re

def check(schema, value, root=None, path="$"):
    root=schema if root is None else root
    if schema is True: return []
    if schema is False: return [path+" is forbidden"]
    if not isinstance(schema,dict): return [path+" has a non-object schema"]
    errors=[]
    known={"$schema","$id","$comment","$defs","definitions","title","description","examples","default","readOnly","writeOnly","deprecated","type","enum","const","properties","required","additionalProperties","items","minItems","maxItems","minLength","maxLength","minimum","maximum","exclusiveMinimum","exclusiveMaximum","pattern","uniqueItems","minProperties","maxProperties","anyOf","allOf","oneOf","not","$ref","format"}
    if set(schema)-known: errors.append(path+" unverified schema keywords: "+", ".join(sorted(set(schema)-known)))
    if "$ref" in schema:
        ref=schema["$ref"]
        if not isinstance(ref,str) or not ref.startswith("#/"): errors.append(path+" unresolved schema reference")
        else:
            node=root
            try:
                for part in ref[2:].split("/"):node=node[part.replace("~1","/").replace("~0","~")]
                if node is schema:errors.append(path+" cyclic schema reference")
                else:errors+=check(node,value,root,path)
            except (KeyError,TypeError,RecursionError):errors.append(path+" unresolved or cyclic schema reference")
    types={"object":isinstance(value,dict),"array":isinstance(value,list),"string":isinstance(value,str),"boolean":type(value) is bool,"integer":type(value) is int or (type(value) is float and value.is_integer()),"number":type(value) in (int,float),"null":value is None}
    expected=schema.get("type")
    if expected:
        options=expected if isinstance(expected,list) else [expected]
        if not any(types.get(s,False) for s in options):return errors+[path+" must be "+" or ".join(options)]
    def equal(a,b):
        if isinstance(a,bool)!=isinstance(b,bool):return False
        return a==b
    if "enum" in schema and not any(equal(value,v) for v in schema["enum"]):errors.append(path+" outside enum")
    if "const" in schema and not equal(value,schema["const"]):errors.append(path+" differs from const")
    if isinstance(value,dict):
        props=schema.get("properties",{})
        for k in schema.get("required",[]):
            if k not in value:errors.append(path+" missing "+k)
        for k,v in value.items():
            if k in props:errors+=check(props[k],v,root,path+"."+k)
            elif "additionalProperties" in schema:errors+=check(schema["additionalProperties"],v,root,path+"."+k)
        if len(value)<schema.get("minProperties",0) or len(value)>schema.get("maxProperties",float("inf")):errors.append(path+" wrong property count")
    if isinstance(value,list):
        if len(value)<schema.get("minItems",0) or len(value)>schema.get("maxItems",float("inf")):errors.append(path+" wrong item count")
        if schema.get("uniqueItems") and any(any(equal(v,z) for z in value[:j]) for j,v in enumerate(value)):errors.append(path+" duplicate items")
        if "items" in schema:
            for i,element in enumerate(value):errors+=check(schema["items"],element,root,f"{path}[{i}]")
    if isinstance(value,str):
        if len(value)<schema.get("minLength",0) or len(value)>schema.get("maxLength",float("inf")):errors.append(path+" wrong string length")
        if "pattern" in schema and not re.search(schema["pattern"],value):errors.append(path+" pattern mismatch")
    if types["number"]:
        if value<schema.get("minimum",float("-inf")) or value>schema.get("maximum",float("inf")):errors.append(path+" outside numeric limits")
        if "exclusiveMinimum" in schema and value<=schema["exclusiveMinimum"]:errors.append(path+" below exclusive minimum")
        if "exclusiveMaximum" in schema and value>=schema["exclusiveMaximum"]:errors.append(path+" above exclusive maximum")
    for op in ("allOf","anyOf","oneOf"):
        if op in schema:
            results=[check(s,value,root,path) for s in schema[op]]
            matches=sum(not res for res in results)
            if op=="allOf" and matches!=len(results): errors.extend(e for res in results for e in res)
            if op=="anyOf" and not matches:errors.append(path+" no anyOf branch matched")
            if op=="oneOf" and matches!=1:errors.append(path+" must match exactly one branch")
    if "not" in schema and not check(schema["not"],value,root,path):errors.append(path+" matched prohibited schema")
    return errors
