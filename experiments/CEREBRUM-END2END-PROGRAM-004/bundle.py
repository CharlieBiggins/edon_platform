"""Source/data handoff only. The trained parent must be supplied separately."""
import io
import zipfile
from core import ROOT, EXPERIMENTS, PARENT, cfg, verify, pinned_bytes, write_once, write_json, digest


def bundle():
    reg=verify()
    files={}
    prefix="edon/experiments/"
    for name,h in reg["inherited_sources"].items():files[prefix+name]=pinned_bytes(EXPERIMENTS/name,h)
    files[prefix+PARENT.name+"/registration.json"]=pinned_bytes(PARENT/"registration.json",cfg()["parent_registration_sha256"])
    for name in (*reg["sources"],*reg["data"],"registration.json"):
        files[prefix+ROOT.name+"/"+name]=(ROOT/name).read_bytes()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            item=zipfile.ZipInfo(name,date_time=(2026,9,10,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(item,data)
    payload=stream.getvalue()
    write_once(ROOT/"exports/program004-handoff.zip",payload)
    result={"bundle_sha256":digest(payload),"bytes":len(payload),"files":len(files),
        "parent_adapter_included":False,"confirmation_included":False,
        "registration_sha256":digest((ROOT/"registration.json").read_bytes())}
    write_json(ROOT/"exports/program004-handoff.json",result)
    return result