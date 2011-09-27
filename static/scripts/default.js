function include_dom(script_filename) {
    var html_doc = document.getElementsByTagName('head').item(0);
    var js = document.createElement('script');
    js.setAttribute('language', 'javascript');
    js.setAttribute('type', 'text/javascript');
    js.setAttribute('src', script_filename);
    js.setAttribute('origin-id', "pluric");
    // Remove any OTHER scripts by me
    $('script[origin-id*=pluric]').remove();
    html_doc.appendChild(js);
    return false;
}


$(document).bind("ready", function() {
    $('a.internal').each( function ()
    {            
        $(this).click(function()
            {   
            $("#spinner").height($(this).parent().height());
            $("#spinner").width($(this).parent().width());
            $("#spinner").css("top", $(this).parent().offset().top).css("left", $(this).parent().offset().left).show()
            include_dom($(this).attr('link-destination') + "?js=yes");
            return false;
            });
        $(this).attr("link-destination",this.href);
    });
$('#spinner').hide();
});
