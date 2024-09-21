function render_immowelt_links ( data, type, row, meta ) {
    if(type === 'display'){
        data = '<a href="https://www.immowelt.de/expose/' + encodeURIComponent(data) + '" target="_blank">' + data + '</a>';
    }
    return data;
}
