function possibly_hide_sites() {
    if (isMiro()) {
        if (parseFloat(MiroVersion()) < 2) {
            // expose the old miro version warning
            $('#oldmiro_warning').css('display', 'block');
            $('#sites_column').css('display', 'none');
        }
    }
}