var FrontifyFinder=function(f){"use strict";function c(t,e){switch(t){case"warning":break;case"error":console.error(`${e.code}: ${e.message}`,e.error||"");break}}class r extends Error{constructor(e,n){super(`${e}: ${n}`);this.code=e,c("error",{code:e,message:n})}}function v(t){const e="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";let n=new Uint8Array(t);return window.crypto.getRandomValues(n),n=n.map(o=>e.charCodeAt(o%e.length)),String.fromCharCode.apply(null,Array.from(n))}function F(t){return btoa(t).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"")}function k(t){return Object.keys(t).filter(e=>t[e]).map(e=>`${e}=${encodeURIComponent(t[e])}`).join("&")}function E(t){const e=t.replace(/^(http(?:s)?:\/\/)/,"");return e.endsWith("/")?e.replace(/\/+$/,""):e}async function _(t,e){return fetch(t,e).then(async n=>{if(n.status>=200&&n.status<=299)return await n.json();throw new r("ERR_AUTH_HTTP_REQUEST",n.statusText)}).then(n=>n).catch(n=>{throw n instanceof r?n:new r("ERR_AUTH_HTTP_REQUEST",n)})}function P(t,e){return window.addEventListener(t,e),()=>{window.removeEventListener(t,e)}}const L="Authorize Frontify",H={title:L,width:800,height:600,top:50,left:50},a=class{constructor(t){this.listeners={},this.domain="",this.attachEventListeners=()=>n=>{switch(n.data){case a.EVENT_NAME_CANCELLED:this.call(a.EVENT_METHOD_CANCELLED);break;case a.EVENT_NAME_SUCCESS:this.call(a.EVENT_METHOD_SUCCESS);break;default:n.data.domain?(this.setDomain(n.data.domain),this.call(a.EVENT_METHOD_DOMAIN)):n.data.aborted&&this.call(a.EVENT_METHOD_ABORTED);break}};const e={...H,...t};this.popUp=a.openPopUp(e),this.unregisterEventListener=P("message",this.attachEventListeners()),this.interval=setInterval(()=>{this.popUp&&this.popUp.closed&&(clearInterval(this.interval),this.call(a.EVENT_METHOD_CANCELLED),this.call(a.EVENT_METHOD_ABORTED))},100)}static openPopUp(t){const e=window.open("about:blank",t.title,`width=${t.width}, 
            height=${t.height}, 
            left=${t.left}, 
            top=${t.top}, 
            toolbar=no, menubar=no, 
            location=no, status=no, 
            directories=no, titlebar=no`);if(!e)throw new r("ERR_AUTH_POPUP_BLOCKED","Popup is blocked. Make sure to enable popups.");return e}call(t){this.listeners[t]&&this.listeners[t]()}setDomain(t){this.domain=t}getDomain(){return this.domain}onDomain(t){this.listeners.domain=t}onAborted(t){this.listeners.aborted=t}onSuccess(t){this.listeners.success=t}onCancelled(t){this.listeners.canceled=t}close(){this.listeners={},clearInterval(this.interval),this.unregisterEventListener(),this.popUp&&!this.popUp.closed&&this.popUp.close()}navigateToUrl(t){if(this.popUp&&!this.popUp.closed){this.popUp.location.replace(t);return}throw new r("ERR_AUTH_POPUP_CLOSED","Popup is closed.")}};let l=a;l.EVENT_NAME_CANCELLED="frontify-oauth-authorize-cancelled",l.EVENT_NAME_SUCCESS="frontify-oauth-authorize-success",l.EVENT_METHOD_CANCELLED="cancelled",l.EVENT_METHOD_SUCCESS="success",l.EVENT_METHOD_DOMAIN="domain",l.EVENT_METHOD_ABORTED="aborted";const M=64,$="code",V="S256",N="/connection/authenticator",x="authorization_code",z="SHA-256",j="Bearer";async function W(t){const e=new TextEncoder().encode(t),n=await window.crypto.subtle.digest(z,e),o=String.fromCharCode.apply(null,Array.from(new Uint8Array(n)));return F(o)}async function B(t){try{const e=v(M),n=await W(e),o=await K(t.domain)||"";return{authorizationUrl:`https://${E(t.domain)}/api/oauth/authorize?${k({response_type:$,client_id:t.clientId,scope:t.scopes.join("+"),code_challenge:n,code_challenge_method:V,redirect_uri:N,session_id:o})}`,codeVerifier:e,sessionId:o}}catch{throw new r("ERR_AUTH_COMPUTE_URL","Error computing authorization url.")}}async function K(t){try{return(await _(`https://${E(t)}/api/oauth/create/session`,{method:"POST"}))?.data.key}catch{throw new r("ERR_AUTH_SESSION","Error generating session.")}}async function q(t,e){try{return(await _(`https://${E(t.domain)}/api/oauth/poll`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({session_id:e})}).catch(()=>{throw new r("ERR_AUTH_POLL_REQUEST","Error requesting oauth session poll.")})).data.payload.code}catch{throw new r("ERR_AUTH_POLL","Error polling oauth session.")}}async function Q(t,e,n){try{const o=E(t?.domain),s=await _(`https://${o}/api/oauth/accesstoken`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({grant_type:x,code:e,code_verifier:n,client_id:t.clientId,redirect_uri:N})});return{bearerToken:{tokenType:j,expiresIn:s.expires_in,accessToken:s.access_token,refreshToken:s.refresh_token,domain:o},clientId:t.clientId,scopes:t.scopes}}catch{throw new r("ERR_AUTH_ACCESS_TOKEN","Error retrieving token.")}}async function J(t,e){try{await _(`https://${E(t)}/api/oauth/revoke`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:e})})}catch{throw new r("ERR_AUTH_TOKEN_REVOKE","Error revoking token.")}}const Y="https://app.frontify.com/finder",G="Authorize Frontify",i={open:!1};let h,m,g,w;async function X(t,e){if(i.open&&h.close(),h=ne(e??{title:G,width:800,height:600,top:50,left:50}),i.open=!0,t.domain?await O(t,h).then(n=>{i.open=!1,n&&(m=n)}).catch(n=>{throw n===!1?new r("ERR_AUTH_POPUP_CLOSED","Auth aborted by client."):new r("ERR_AUTH_FAILED","Auth failed.")}):await ee(t,h).then(n=>{i.open=!1,m=n}).catch(n=>{throw n===!1?new r("ERR_AUTH_DOMAIN_POPUP_CLOSED","Domain cancelled by client."):new r("ERR_AUTH_FAILED","Auth failed.")}),!m)throw new r("ERR_AUTH_NO_TOKEN","No token returned.");return m}async function Z(t){return await J(t.bearerToken.domain,t.bearerToken.accessToken),t}async function O(t,e){try{const n=await B(t);return await te(n.authorizationUrl,e).then(async()=>{const o=await q(t,n.sessionId);return Q(t,o,n.codeVerifier)})}catch(n){const o="Error generating session. Make sure that the inserted domain is a valid and secure Frontify instance.";throw e.popUp?.postMessage({domainError:o},"*"),n instanceof r&&n.code==="ERR_AUTH_COMPUTE_URL"?new r("ERR_AUTH_SESSION","Failed generating session."):(i.open=!1,new r("ERR_AUTH","Failed retrieving access token."))}}function ee(t,e){return e.navigateToUrl(Y),c("warning",{code:"WARN_DOMAIN_POPUP_OPEN",message:"Domain popup opened."}),new Promise((n,o)=>{g=setTimeout(()=>{i.open=!1,e.close(),c("warning",{code:"WARN_DOMAIN_TIMEOUT",message:"Domain popup timed out."})},5*60*1e3),e.onDomain(()=>{clearTimeout(g),t.domain=h.getDomain(),O(t,h).then(s=>{s&&n(s)}).catch(s=>{s instanceof r&&s.code!=="ERR_AUTH_SESSION"?o():delete t.domain}),c("warning",{code:"WARN_DOMAIN_SELECT",message:"Domain input submitted."})}),e.onAborted(()=>{i.open=!1,clearTimeout(g),e.close(),o(!1)})})}function te(t,e){return e.navigateToUrl(t),c("warning",{code:"WARN_AUTH_POPUP_OPEN",message:"Auth popup opened."}),new Promise((n,o)=>{w=setTimeout(()=>{i.open=!1,e.close(),c("warning",{code:"WARN_AUTH_TIMEOUT",message:"Auth popup timed out."})},5*60*1e3),e.onAborted(()=>{i.open=!1,clearTimeout(w),e.close(),o(!1)}),e.onSuccess(()=>{i.open=!1,clearTimeout(w),e.close(),c("warning",{code:"WARN_AUTH_SUCCESS",message:"Auth success."}),n()}),e.onCancelled(()=>{i.open=!1,clearTimeout(w),e.close(),o(!1)})})}function ne(t){return new l(t??{})}class oe{constructor(){this.length=0}key(){return null}clear(){for(const e of Object.keys(this))this.removeItem(e)}getItem(e){return typeof this[e]!="string"?null:this[e]}removeItem(e){typeof this[e]=="string"&&delete this[e]}setItem(e,n){this[e]=n}}function d(t,e){switch(t){case"warning":break;case"error":console.error(`${e.code}: ${e.message}`,e.error||"");break}}class u extends Error{constructor(e,n){super(`${e}: ${n}`);this.code=e,d("error",{code:e,message:n})}}function I(){return"FRONTIFY_FINDER"}function T(t){return`${I()}-${t}`}async function se(t,e){return fetch(t,e).then(async n=>{if(n.status>=200&&n.status<=299)return await n.json();throw new u("ERR_FINDER_HTTP_REQUEST",n.statusText)}).then(n=>n).catch(n=>{throw n instanceof u?n:new u("ERR_FINDER_HTTP_REQUEST",n.message)})}const p={key:`${I()}_test`,value:"yes"};let y;function R(){return y===void 0&&(y=ce()),y}function b(){return Math.floor(Date.now()/1e3)}function re(t){return t<b()}function A(t){R().removeItem(t)}function ie(t,e,n){const o={expiresAt:n?b()+n:void 0,data:e};R().setItem(t,JSON.stringify(o))}function ae(t){const e=S(t);return e&&A(t),e}function S(t){const e=R().getItem(t);if(!e)return;const n=JSON.parse(e);if(!n){A(t);return}if(n.expiresAt&&re(n.expiresAt)){A(t);return}return n.data}function ce(){return D("localStorage")?window.localStorage:D("sessionStorage")?window.sessionStorage:new oe}function D(t){try{if(typeof window[t]=="undefined")return!1;const e=window[t];return e.setItem(p.key,p.value),e.getItem(p.key)===p.value?(e.removeItem(p.key),!0):!1}catch(e){return!1}}const le=`
query AssetByIds($ids: [ID!]!) {
  assets(ids: $ids) {
    id
    title
    description
    type: __typename
    creator {
      name
    }
    createdAt
    expiresAt
    ...withMetadata
    ...onImage
    ...onDocument
    ...onFile
    ...onAudio
    ...onVideo
  }
}

fragment withMetadata on Asset {
  tags {
    value
    source
  }
  metadataValues {
    value
    metadataField {
      id
      label
    }
  }
  copyright {
    status
    notice
  }
  licenses {
    title
    text: license
  }
}

fragment onImage on Image {
  author
  filename
  extension
  size
  downloadUrl(validityInDays: 1)
  previewUrl
  width
  height
  focalPoint
}

fragment onFile on File {
  author
  filename
  extension
  size
  downloadUrl(validityInDays: 1)
  icon: previewUrl
}

fragment onDocument on Document {
  author
  filename
  extension
  size
  pageCount
  downloadUrl(validityInDays: 1)
  previewUrl
  focalPoint
}

fragment onAudio on Audio {
  author
  filename
  extension
  size
  downloadUrl(validityInDays: 1)
  previewUrl
}

fragment onVideo on Video {
  author
  filename
  extension
  size
  downloadUrl(validityInDays: 1)
  previewUrl
  width
  height
  duration
  bitrate
}
`;async function de({domain:t,bearerToken:e},n){const o=await se(`https://${t}/graphql`,{method:"POST",headers:{"content-type":"application/json",authorization:`Bearer ${e}`,"x-frontify-beta":"enabled"},body:JSON.stringify({query:le,variables:{ids:n}})}).then(s=>s);if(o.errors&&d("error",{code:"ERR_FINDER_ASSETS_REQUEST",message:"Assets data request failed.",error:o.errors[0]}),!o?.data?.assets||o.data.assets.length===0)throw new u("ERR_FINDER_ASSETS_REQUEST_EMPTY","Assets data request returned no valid values.");return o.data.assets.map(s=>(s.previewUrl&&(s.previewUrl=s.previewUrl.split("?")[0]),s))}class U{constructor(e,n,o){this.token=e,this.options=n,this.onLogoutRequested=o,this.listeners={},this.iFrame=ue(e.bearerToken.domain)}static get VERSION(){return 2}subscribeToFinderEvents(){const e=this.parentNode?.ownerDocument?.defaultView||window;this.unsubscribe=he(e,"message",n=>{if(!(this.iFrame.contentWindow!==n.source||n.origin!==this.origin)){if(n.data.configurationRequested){this.initialize();return}if(n.data.assetsChosen){try{this.handleAssetsChosen(n.data.assetsChosen.map(o=>o.id))}catch(o){throw o}return}if(n.data.aborted){this.handleFinderCancel();return}if(n.data.logout){this.onLogoutRequested(),this.handleFinderCancel();return}d("warning",{code:"WARN_FINDER_UNKNOWN_EVENT",message:"Unknown event from Frontify Finder."})}})}get origin(){return`https://${this.token.bearerToken.domain}`}get domain(){return this.token.bearerToken.domain}get accessToken(){return this.token.bearerToken.accessToken}initialize(){this.iFrame?.contentWindow?.postMessage({version:U.VERSION,token:this.accessToken,supports:{cancel:!0,logout:!0},multiSelectionAllowed:this.options?.allowMultiSelect??!1,filters:this.options?.filters},this.origin)}handleFinderCancel(){this.options.autoClose&&this.close(),this.listeners.cancel&&this.listeners.cancel()}async handleAssetsChosen(e){try{const n=await de({domain:this.domain,bearerToken:this.accessToken},e);this.options?.autoClose&&this.close(),this.listeners.assetsChosen&&this.listeners.assetsChosen(n)}catch(n){n instanceof u||d("error",{code:"ERR_FINDER_ASSETS_SELECTION",message:"Failed retrieving assets data."})}}onAssetsChosen(e){return this.listeners.assetsChosen=e,this}onCancel(e){return this.listeners.cancel=e,this}mount(e){if(this.parentNode)throw new u("ERR_FINDER_ALREADY_MOUNTED","Frontify Finder already mounted on a parent node.");this.parentNode=e,this.subscribeToFinderEvents(),this.parentNode.appendChild(this.iFrame)}close(){try{this.unsubscribe&&this.unsubscribe(),this.parentNode&&this.parentNode.removeChild(this.iFrame)}catch(e){d("error",{code:"ERR_FINDER_CLOSE",message:"Error closing Frontify Finder."})}finally{delete this.parentNode,delete this.unsubscribe}}}function ue(t){const e=document.createElement("iframe");return e.style.border="none",e.style.outline="none",e.style.width="100%",e.style.height="100%",e.style.display="block",e.className="frontify-finder-iframe",e.src=`https://${t}/external-asset-chooser`,e.name="Frontify Finder",e.sandbox.add("allow-same-origin"),e.sandbox.add("allow-scripts"),e}function he(t,e,n){const o=s=>{n(s)};return t.addEventListener(e,o),()=>{t.removeEventListener(e,o)}}const Ee=["basic:read","finder:read"],pe=300,fe={autoClose:!1,allowMultiSelect:!1,filters:[]};async function _e({clientId:t,domain:e,options:n},o){if(!me({clientId:t})){const Te=await X({domain:e,clientId:t,scopes:Ee},o).then(ge=>ge).catch(()=>{d("error",{code:"ERR_FINDER_AUTH_FAILED",message:"Authentication Failed!"})});we(Te,{clientId:t})}const s=S(T(t));if(!s)throw new u("ERR_FINDER_ACCESS_STORED_TOKEN","Error accessing stored token.");return new U(s,n??fe,async()=>{await C({clientId:t}),d("warning",{code:"WARN_USER_LOGOUT",message:"User successfully logged out"})})}async function C({clientId:t}){const e=T(t),n=ae(e);n&&await Z(n)}function me({clientId:t}){const e=T(t);return!!S(e)}function we(t,{clientId:e}){const n=t.bearerToken.expiresIn-pe,o=T(e);ie(o,t,n)}return f.create=_e,f.logout=C,Object.defineProperty(f,"__esModule",{value:!0}),f}({});
//# sourceMappingURL=index.js.map
