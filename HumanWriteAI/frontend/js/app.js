
async function upload(){

let file=document.getElementById("file").files[0];

let form=new FormData();

form.append("file",file);

let response=await fetch(
"http://127.0.0.1:5000/api/documents/upload",
{
method:"POST",
body:form
}
);

let data=await response.json();

document.getElementById("result").innerText=
JSON.stringify(data,null,2);

}
