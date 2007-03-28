/* feature_rotate.js
 * 
 * Does the feature rotate animation.
 */

var FEATURED_CHANNEL_WIDTH = 390;
var FEATURED_2_CHANNELS_WIDTH = 760;
var FEATURE_ROTATE_TIMEOUT = 15; // rotate timeout in seconds
var featureList = null;

function scheduleFeatureRotate() {
   loadHiddenScreenshots();
   if(!featureList) featureList = findFeatures();
   setTimeout(rotateFeatures, FEATURE_ROTATE_TIMEOUT * 1000);
}

function loadHiddenScreenshots() {
   var i = 1;
   while(true) {
     var screenshot = document.getElementById('feature-screenshot-' + i);
     i += 1;
     if(!screenshot) break;
     var fakeScreenshot = screenshot.childNodes[0];
     if(fakeScreenshot.nodeType != 3) continue;
     var re = /src:\s*"([^"]*)".*alt:\s*"([^"]*)"/
     var matches = re.exec(fakeScreenshot.nodeValue);
     if(!matches) continue;
     realScreenshot = new Image(); 
     realScreenshot.src = matches[1];
     realScreenshot.alt = matches[2];
     screenshot.replaceChild(realScreenshot, fakeScreenshot);
  }
}

function rotateFeatures() {
   FSStartX = FSCurrentFeature * FEATURED_CHANNEL_WIDTH;
   FSCurrentFeature = pickNextFeature();
   FSEndX = FSCurrentFeature * FEATURED_CHANNEL_WIDTH;
   FSTime = 0.0;
   animateFeatureScroll();
}

function pickNextFeature() {
   var nextFeature = FSCurrentFeature + 2*FSScrollDirection;
   if(nextFeature < 0) {
        FSScrollDirection *= -1;
        return 0
   }
   if(nextFeature >= featureList.length-2) {
        FSScrollDirection *= -1;
        return featureList.length-2;
   }
   return nextFeature;
}

function findFeatures() {
   var featuredList = document.getElementById('featured-list');
   var features = new Array();
   var currentFeature = featuredList.firstChild;
   if(currentFeature && currentFeature.nodeType != Node.ELEMENT_NODE) 
      currentFeature = getNextElement(currentFeature);
   while(currentFeature) {
        features.push(currentFeature);
        currentFeature = getNextElement(currentFeature);
   }
   return features;
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
       scheduleFeatureRotate();
   }
}

function moveFeatureList(leftX) {
   var featuredList = document.getElementById('featured-list');
   featuredList.style.left = '-' + leftX + 'px';
}

// Translates the feature scroll time into a position.  Ranges from 0 to 1,
// like FSTime, but gets transformed using a cosine for nice, non-linear
// movement.
function FSCalcPosition() {
  return (1 - Math.cos(FSTime * Math.PI)) / 2;
}
