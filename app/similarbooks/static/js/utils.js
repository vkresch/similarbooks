function render_gutenberg_links ( data, type, row, meta ) {
    if(type === 'display'){
        data = '<a href="https://www.gutenberg.de/expose/' + encodeURIComponent(data) + '" target="_blank">' + data + '</a>';
    }
    return data;
}
