function include_dom(script_filename) {
    var html_doc = document.getElementsByTagName('head').item(0);
    var js = document.createElement('script');
    js.setAttribute('language', 'javascript');
    js.setAttribute('type', 'text/javascript');
    js.setAttribute('src', script_filename);
    js.setAttribute('origin-id', "pluric");
    $('script[src*="js=yes"]').remove();
    html_doc.appendChild(js);
    return false;
}


$(document).bind("ready", function() {


    if ($("#centerandright").length)
    {
   
        // Main vertical splitter, anchored to the browser window
        $("#content").splitter({
            type: "v",
            outline: true,
            minLeft: 100, sizeLeft: 150,
            anchorToWindow: true,
        });
        // Second vertical splitter, nested in the right pane of the main one.
   
        $("#centerandright").splitter({
            type: "v",
            outline: true,
            minLeft: 100, sizeLeft: 150,
        });
   
   
    /*

        $("#centerandright").splitter({
            type: "h",
            outline: true,
            minTop: 100,
            minBottom: 300,
            anchorToWindow: true,

        });

     */

 }




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

    $(".vote").submit(function(event) {
        voteref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var $form = $( this ),
            rating = $form.find( 'input[name="rating"]' ).val(),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, { 'rating': $form.find( 'input[name="rating"]' ).val(),
                       '_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(), 
                       'hash' : $form.find( 'input[name="hash"]' ).val() },
          function( data ) {
              voteref.parent().empty().append( data );
          }
        );
    });
    $(".reply").click(function(event) {
        event.preventDefault();
        var $msg = $(this).attr('message');
        var $href = $(this).attr('href');
        $.get($href + "?getonly=true",function(data) {
          $('#reply_'+$msg).empty().append("<br>" + data);
        });   
        
    });    
  
});
