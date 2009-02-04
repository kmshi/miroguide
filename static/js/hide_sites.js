function possibly_hide_sites() {
    if (isMiro()) {
        if (parseFloat(MiroVersion()) < 2) {
            // expose the old miro version warning
            $('#oldmiro_warning').css('display', 'block');
            $('#sites_column').css('display', 'none');
        } else if (navigator.appVersion.indexOf("X11") != -1) {
            // Probably Linux (maybe BSD or something too)
            $('#linux_warning').css('display', 'block');
        }
    }
}