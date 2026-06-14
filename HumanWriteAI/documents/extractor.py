
from docx import Document

def extract_text(file):

    doc=Document(file)

    text=[]

    for p in doc.paragraphs:
        text.append(p.text)

    return "\n".join(text)
