/* channelguide.js
 * 
 * Shared functions used in channel guide
 */

function getPreviousElement(elt) {
    while(elt.previousSibling) {
        elt = elt.previousSibling;
        if(elt.nodeType == 1) return elt;
    }
    return null;
}

function getNextElement(elt) {
    while(elt.nextSibling) {
        elt = elt.nextSibling;
        if(elt.nodeType == 1) return elt;
    }
    return null;
}

function showLoadIndicator() {
    document.getElementById('load-indicator').style.display = 'block';
}

function makeXMLHttpRequest() {
    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        return new XMLHttpRequest();
    } else if (window.ActiveXObject) { // IE
        try {
            return new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {}
        try {
            return new ActiveXObject("Microsoft.XMLHTTP");
        } catch (e) {}
    }
    return null;
}

function ajaxLink(url, id) {
    var request = makeXMLHttpRequest();
    var elt = document.getElementById(id);
    if (!request || !elt) return true;
    request.onreadystatechange = function() {
         if (request.readyState == 4) {
            if (request.status == 200) {
                elt.innerHTML = request.responseText;
            }
         }
    };
    request.open('GET', url, true);
    request.send(null);
    return false;
}
