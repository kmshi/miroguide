    
function isMSIE() {
    return (navigator.userAgent.indexOf('MSIE') != -1);
}

function showDonateRibbon() {
    var ribbon = $("#donate");
    ribbon.children('.amounts').show();
    ribbon.children('.types').hide();
    ribbon.attr('style', 'display: none;');
    $("#video").hide();
    if (!isMSIE()) {
	ribbon.css('opacity', 0.6);
    }
    ribbon.show();
    if (!isMSIE()) {
	everythingElse = $("#header").add(".column.left").add(".column.right > *");
	everythingElse.css('opacity', "0.6");
	ribbon.animate({opacity: 1}, 'fast');
    }
}
function hideDonateRibbon() {
    ribbon = $("#donate");
    everythingElse = $("#header").add(".column.left").add(".column.right > *");
    if (!isMSIE()) {
	everythingElse.animate({ opacity: 1}, 'fast', function() {
	    everythingElse.css('opacity', '1');});
	ribbon.animate({opacity: 0}, 'fast',
		       function() {
			   ribbon.hide();
			   $("#video").show();
		       });	
    } else {
	ribbon.hide();
	$("#video").show();
    }
}

    
$(document).ready(function () {
    $("#donate .amounts div").click(function () {
	var amount;
	if ($(this).hasClass('other')) {
	    amount = $(this).children('input').val();
	    if (!amount) {
		$(this).children('input').css('border-color', 'red');
		return;
	    }
	} else {
	    amount = $(this).attr('amount');
	}
	paypal = $("#donate .types a:eq(0)");
	if (!paypal.attr('oldHref'))
	    paypal.attr('oldHref', paypal.attr('href'));
	paypal.attr('href', paypal.attr('oldHref') + '&amount=' + amount);
	cc = $("#donate .types a:eq(1)");
	if (!cc.attr('oldHref'))
	    cc.attr('oldHref', cc.attr('href'));
	cc.attr('href', cc.attr('oldHref') + '?' + amount);
	$("#donate .types").show();
	$("#donate .amounts").hide();
    });
    $("#donate .amounts input").keypress(function(e) {
	if (e.which == 13) $(this).parent().click();
    }).click(function() {return false;});
});

function setThanksTimeout(url) {
    $("#donate a:lt(2)").click(function () {
	setTimeout(function() {
	    document.location = url;
	}, 1000);
	return true;
    });
}

function vlcPlayPause(obj, button) {
    if (obj.isplaying() == true) { 
        obj.pause();
        button.attr('value', 'Play');
    } else { 
        obj.play();
        button.attr('value', 'Pause');
    }
}

function vlcRestart(obj) {
    obj.stop();
    obj.play();
}

function createVideo(obj, flv, mp4, image, width, height) {
    win = 0;
    var htmlCode = '';
    if (navigator.mimeTypes['application/x-shockwave-flash'] &&
	navigator.mimeTypes['application/x-shockwave-flash'].enabledPlugin) {
        var htmlCode = '<embed ' +
    	    'src="http://s3.miroguide.com/static/images/mediaplayer.swf" '+
    	'width="' + width + '" ' +
	'height="' + height + '" ' +
	'allowscriptaccess="always" ' +
	'allowfullscreen="true" ' +
	'flashvars="height=' + height + '&width=' + width + '&file=' + flv +
	'&image=' + image + '&showdigits=false&usefullscreen=false" '+
	'/>';    
    } else if (navigator.mimeTypes["application/x-vlc-plugin"] &&
	navigator.mimeTypes["application/x-vlc-plugin"].enabledPlugin) {
        /* use VLC */
        htmlCode = '<embed type="application/x-vlc-plugin" width=' + width + ' height=' + height + ' autoplay="no" loop="no" name="video1" target="' + mp4 + '" />'
            + '<input id="playpause" type="button" value="Play" onclick="vlcPlayPause(document.video1, $(\'#playpause\'));" />'
            + '<input type="button" value="Restart" onclick="vlcRestart(document.video1);" />'
            + '<input type="button" value="Mute" onclick="document.video1.mute(); document.video1.get_volume();" />'
        win = 1;
        height = height + 23;
    } else if (navigator.mimeTypes["video/quicktime"] &&
	       navigator.mimeTypes["video/quicktime"].enabledPlugin) {
        height = height + 19;
        htmlCode = '<object classid="clsid:02BF25D5-8C17-4B23-BC80-D3488ABDDC6B" id="player" height="' + height +'" width="' + width + '">' +
            '<param name="CONTROLS" value="imagewindow">'+
            '<param name="autogotourl" value="false">'+
            '<param name="console" value="radio">'+
            '<param name="autostart" value="false">'+
            '<param name="type" value="video/quicktime">'+
            '<param name="src" value="' + mp4 + '">'+
            '<embed controls="imagewindow" autogotourl="false" console="radio" autostart="false" type="video/quicktime" src="' + mp4 + '" name="player" height="' + height +'" width="' + width + '">'+
            '</object>';
    }
    if (htmlCode != '') {
        obj.html(htmlCode).height(height);
        if (win) {
            for (var i=10; i<=100; i+= 10) {
                window.setTimeout(function(){
                    document.video1.set_volume(i);
                }, i);
            }
        }
    }
}