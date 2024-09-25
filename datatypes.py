import copy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Union

'''
og: original
fn: filename
'''

@dataclass
class Page:
    uid:str
    og_fn:str
    kra_fn:Path
    def toJSON(self,root:Path):
        return {"uid":self.uid,"og_fn":str(self.og_fn),"kra_fn":str(self.kra_fn.relative_to(root))}
    
    @classmethod
    def fromJSON(cls,dic:dict,root:Path):
        return cls(uid=dic["uid"],
                    og_fn=root/dic["og_fn"],
                    kra_fn=root/dic["kra_fn"])

KRA_FOLDER = "kras"
THM_FOLDER = "thms"
THM_RECT = 256

class Project:
    title: str
    pages: list[Page]
    root_path: Path

    def __init__(self,root_path:Path) -> None:
        self.root_path=Path(root_path)
        self.pages=[]
        self.title = ""
        kras_folder = self.root_path / KRA_FOLDER
        kras_folder.mkdir(parents=True, exist_ok=True)
        thms_folder = self.root_path / THM_FOLDER
        thms_folder.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls,path:Path):
        meta=json.loads(path.read_bytes())
        new_inst = cls((path.parent/meta["root_path"]).absolute().resolve())
        new_inst.pages=[Page.fromJSON(x,new_inst.root_path) for x in meta["pages"]]
        new_inst.title=meta["title"]
        return new_inst
    
    @property
    def uids(self):
        return [x.uid for x in self.pages]
    
    @property
    def thms(self):
        return [self.root_path/THM_FOLDER/(x.uid+".jpg") for x in self.pages]
    
    def add_page(self,krita_inst,file_path:Union[Path,str]):
        file_path = Path(file_path)
        uid = file_path.stem
        uids = set(self.uids)
        while uid in uids:
            uid+="_"

        kra_path = self.root_path / KRA_FOLDER / (uid + ".kra")
        thm_path = self.root_path / THM_FOLDER / (uid + ".jpg")
        
        doc = krita_inst.openDocument(str(file_path))
        
        # Save .kra
        doc.setBatchmode(True)
        doc.saveAs(str(kra_path))

        # Save Thumbnail
        w,h=doc.width(),doc.height()
        r=THM_RECT/max(w,h)
        rw,rh=int(w*r),int(h*r)
        doc.thumbnail(rw,rh).save(str(thm_path))
        doc.close()

        self.pages.append(Page(uid,file_path.name,kra_path))

    def save(self):
        jsons=copy.deepcopy(vars(self))
        jsons["root_path"] = "."
        jsons["pages"] = [x.toJSON(self.root_path) for x in jsons["pages"]]
        (self.root_path/"project.json").write_text(json.dumps(jsons,ensure_ascii=False))


        
