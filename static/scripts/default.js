function include_dom(script_filename) {
    var html_doc = document.getElementsByTagName('head').item(0);
    var js = document.createElement('script');
    js.setAttribute('language', 'javascript');
    js.setAttribute('type', 'text/javascript');
    js.setAttribute('src', script_filename);
    html_doc.appendChild(js);
    return false;
}


$(document).ready(function() {


    $('a.internal').each( function ()
    {            
        $(this).click(function()
            {   
                $('spinner').width($(content).width());
                $('spinner').height($(content).height()); 
                $('spinner').html("TEST!");
                $('spinner').show();
                include_dom($(this).attr('link-destination') + "?js=yes");
                $('spinner').hide();
                return false;
            });
        $(this).attr("link-destination",this.href);
    });
});
