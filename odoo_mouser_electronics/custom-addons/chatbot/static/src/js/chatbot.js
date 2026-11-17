/** @odoo-module **/

class ChatbotWidget {

constructor(){

this.chatWindow=null;
this.chatToggle=null;
this.messagesContainer=null;

this.inputField=null;

this.sendButton=null;

this.closeButton=null;

this.micButton=null;

this.recognition=null;

this.initialized=false;

this.init();

}


/* INIT */

init(){

if(document.readyState==="loading"){

document.addEventListener(
"DOMContentLoaded",
()=>this.initializeWidget()
);

}

else{

this.initializeWidget();

}

}


/* LOAD */

initializeWidget(){

if(this.initialized){
return;
}

this.setupElements();

if(
this.sendButton &&
this.inputField &&
this.messagesContainer
){

this.setupEventListeners();

this.initialized=true;

this.checkStartupState();

}

}


/* ELEMENTS */

setupElements(){

this.chatWindow=
document.getElementById(
"my_chat_window"
);

this.chatToggle=
document.getElementById(
"my_chat_icon"
);

this.messagesContainer=
document.getElementById(
"chat_messages"
);

this.inputField=
document.getElementById(
"chat_input"
);

this.sendButton=
document.getElementById(
"chat_send_btn"
);

this.closeButton=
document.getElementById(
"chat_close_btn"
);

this.micButton=
document.getElementById(
"chat_mic_btn"
);

}


/* EVENTS */

setupEventListeners(){

this.chatToggle
?.addEventListener(
"click",
()=>this.toggleChat()
);

this.closeButton
?.addEventListener(
"click",
()=>this.closeChat()
);

this.sendButton
?.addEventListener(
"click",
(e)=>{

e.preventDefault();

this.sendMessage();

}
);

this.inputField
?.addEventListener(
"keypress",
(e)=>{

if(e.key==="Enter"){

e.preventDefault();

this.sendMessage();

}

}
);

this.micButton
?.addEventListener(
"click",
()=>this.startVoice()
);

}


/* VOICE */

startVoice(){

const SpeechRecognition=

window.SpeechRecognition||

window.webkitSpeechRecognition;


if(!SpeechRecognition){

alert(
"Voice not supported"
);

return;

}


this.recognition=

new SpeechRecognition();

this.recognition.lang="en-US";

this.recognition.interimResults=false;

this.recognition.continuous=false;

this.micButton.innerHTML="🔴";

this.recognition.start();


this.recognition.onresult=(event)=>{

const text=

event.results[0][0]
.transcript;

this.inputField.value=text;

this.sendMessage();

};


this.recognition.onend=()=>{

this.micButton.innerHTML="🎙️";

};

}


/* CHAT */

toggleChat(){

this.chatWindow
?.classList
.toggle(
"active"
);

}

closeChat(){

this.chatWindow
?.classList
.remove(
"active"
);

}

openChat(){

this.chatWindow
?.classList
.add(
"active"
);

}

checkStartupState(){

let query =
localStorage.getItem(
"chatbot_search_query"
);

const userText =
localStorage.getItem(
"chatbot_last_user"
);

const botReply =
localStorage.getItem(
"chatbot_last_reply"
);

if(!query){
const params = new URLSearchParams(
window.location.search
);
query = params.get("search");
}

if(!query && !botReply){
return;
}

localStorage.removeItem(
"chatbot_search_query"
);
localStorage.removeItem(
"chatbot_last_user"
);
localStorage.removeItem(
"chatbot_last_reply"
);

this.openChat();

if(userText){
    this.displayMessage(userText, "user");
}

if(botReply){
    this.displayMessage(botReply, "bot");
}

}


/* WEBSITE SEARCH */

triggerWebsiteSearch(message){

const search=

document.querySelector(
".o_wsale_products_searchbar_input"
)

||

document.querySelector(
'input[name="search"]'
)

||

document.querySelector(
'input[type="search"]'
);


if(!search){
return;
}


/* UPDATE SEARCH BAR ONLY */

search.focus();

search.value=
message;

localStorage.setItem(
"chatbot_search_query",
message
);

const form = search.closest("form");

if (form) {
    form.submit();
    return;
}


/* EVENTS */

search.dispatchEvent(

new Event(
"input",
{
bubbles:true
}
)

);

search.dispatchEvent(

new Event(
"change",
{
bubbles:true
}
)

);

/* NO PAGE REFRESH */

}



/* SEND */

async sendMessage(){

const message=

this.inputField
.value
.trim();


if(!message){
return;
}


/* USER */

this.displayMessage(
message,
"user"
);


/* CLEAR */

this.inputField.value="";


/* LOADER */

this.showTypingIndicator();


/* BOT */

await this.sendToBackend(
message
);


/* WEBSITE */

this.triggerWebsiteSearch(
message
);

}



/* BACKEND */

async sendToBackend(message){

try{

const response=

await fetch(

"/chatbot/message",

{

method:"POST",

headers:{

"Content-Type":
"application/json"

},

body:

JSON.stringify({

jsonrpc:"2.0",

params:{

message

}

})

}

);


const data=

await response.json();


this.removeTypingIndicator();


const reply=

data.result?.reply||

data.reply||

"No response";


localStorage.setItem(
"chatbot_last_reply",
reply
);

this.displayMessage(
reply,
"bot"
);

localStorage.setItem(
"chatbot_last_user",
message
);

}

catch(error){

console.log(
error
);

this.removeTypingIndicator();

this.displayMessage(
"Unable to fetch response",
"bot"
);

}

}


/* DISPLAY */

displayMessage(
text,
sender
){

const div=

document.createElement(
"div"
);


div.classList.add(

"chat-message",

`${sender}-message`

);


const bubble =

document.createElement(
"div"
);

bubble.classList.add(
"chat-bubble"
);

if(sender==="bot"){
    bubble.innerHTML=text;
}
else{
    bubble.textContent=text;
}

div.appendChild(
 bubble
);

this.messagesContainer
.appendChild(
div
);

this.messagesContainer.scrollTop=

this.messagesContainer
.scrollHeight;

}


/* LOADER */

showTypingIndicator(){

this.removeTypingIndicator();

const div=

document.createElement(
"div"
);

div.id=
"typing-indicator";

div.classList.add(

"chat-message",

"bot-message"

);

div.innerHTML=

"<p>Typing...</p>";

this.messagesContainer
.appendChild(
div
);

}


removeTypingIndicator(){

document
.getElementById(
"typing-indicator"
)
?.remove();

}

}


new ChatbotWidget();