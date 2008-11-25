/* feature_rotate.js
 * 
 * Does the feature rotate animation.
 */

var FEATURED_CHANNEL_WIDTH = 242;
var FEATURE_ROTATE_TIMEOUT = 20; // rotate timeout in seconds
var featureList = null;
var featureTimeout = null;
var manualMode = false;
var inRotate = false;

function carouselOnLoad() {
    $("#button_next").click(rotateFeaturesRight);
    $("#button_previous").click(rotateFeaturesLeft);
    scheduleFeatureRotate();
}

function scheduleFeatureRotate() {
   if(manualMode) return;
   // loadHiddenScreenshots();
   if(!featureList) featureList = findFeatures();
   featureTimeout = setTimeout(rotateFeatures, FEATURE_ROTATE_TIMEOUT * 1000);
}

function cancelFeatureRotate() {
   if(featureTimeout) {
       clearTimeout(featureTimeout);
       featureTimeout = null;
   }
   manualMode = true;
}

// function loadHiddenScreenshots() {
//    var i = 1;
//    while(true) {
//      var screenshot = document.getElementById('feature-screenshot-' + i);
//      i += 1;
//      if(!screenshot) break;
//      var fakeScreenshot = screenshot.childNodes[0];
//      if(fakeScreenshot.nodeType != 3) continue;
//      var re = /src:\s*"([^"]*)".*alt:\s*"([^"]*)"/
//      var matches = re.exec(fakeScreenshot.nodeValue);
//      if(!matches) continue;
//      var realScreenshot = document.createElement('img'); 
//      realScreenshot.setAttribute('src', matches[1]);
//      realScreenshot.setAttribute('alt', matches[2]);
//      screenshot.replaceChild(realScreenshot, fakeScreenshot);
//   }
// }

function rotateFeaturesLeft() {
    doRotate(Math.max(0, FSCurrentFeature - 3));
    cancelFeatureRotate();
}

function rotateFeaturesRight() {
    doRotate(Math.min(featureList.length - 3, FSCurrentFeature + 3));
    cancelFeatureRotate();
}

function rotateFeatures() {
   featureTimeout = null;
   doRotate(pickNextFeature());
}

function doRotate(nextFeature) {
   if(inRotate) return;
   inRotate = true;
   FSStartX = FSCurrentFeature * FEATURED_CHANNEL_WIDTH;
   FSCurrentFeature = nextFeature;
   FSEndX = FSCurrentFeature * FEATURED_CHANNEL_WIDTH;
   FSTime = 0.0;
   animateFeatureScroll();
}


function pickNextFeature() {
   var nextFeature = FSCurrentFeature + 3*FSScrollDirection;
   if(nextFeature < 0) {
        FSScrollDirection *= -1;
        return 0
   }
   if(nextFeature >= featureList.length-3) {
        FSScrollDirection *= -1;
        return featureList.length-3;
   }
   return nextFeature;
}

function findFeatures() {
   return $('#featured-list').children();
}


// Variables used in the feature scroll animation.  They are prefixed with FS to
// avoid namespace conflicts.
var FSStartX = 0;
var FSEndX = 0;
var FSTime = 0.0; // Time variable. ranges from 0 to 1.
var FSTimeStep = 0.1;
var FSTimeout = 50;
var FSCurrentFeature = 0;
var FSScrollDirection = 1;

function animateFeatureScroll() {
   if(FSTime < 1.0) {
       moveFeatureList(FSStartX + (FSEndX - FSStartX) * FSCalcPosition());
       FSTime += FSTimeStep;
       setTimeout(animateFeatureScroll, FSTimeout);
   } else {
       moveFeatureList(FSEndX);
       inRotate = false;
       scheduleFeatureRotate();
   }
}

function moveFeatureList(leftX) {
    console.log('movin on up')
    var featuredList = document.getElementById('featured-list');
    featuredList.style.left = '-' + leftX + 'px';
}

// Translates the feature scroll time into a position.  Ranges from 0 to 1,
// like FSTime, but gets transformed using a cosine for nice, non-linear
// movement.
function FSCalcPosition() {
  return (1 - Math.cos(FSTime * Math.PI)) / 2;
}
