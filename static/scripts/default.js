
jQuery().ready(function() {
    $jQuery = jQuery.noConflict();
    var currentelement = "";

    if (jQuery("#centerandright").length)
    {

        VerticalSplitter.SetUpElement({ containerId: "content", firstItemId: "left", secondItemId: "centerandright" });
        VerticalSplitter.SetUpElement({ containerId: "centerandright", firstItemId: "center", secondItemId: "right" });
    }
    // Ensure that if we move Splitter 1 and push splitter2 offscreen, we still redraw it.
    jQuery('.splitter').mouseup(function() {
        VerticalSplitter.SetUpElement({ containerId: "centerandright", firstItemId: "center", secondItemId: "right" });
    });

     function getParameterByName(name) {
         var match = RegExp('[?&]' + name + '=([^&]*)')
                         .exec(window.location.search);
         return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
     }
 
    if (getParameterByName("jumpto"))
    {
        jumpto = getParameterByName("jumpto")
        //Ensure we can't jump to random stuff.
        var alphanumberic = /^([a-zA-Z0-9_-]+)jQuery/;
        if(alphanumberic.test( jumpto ))
        {    
            // If the element exists, find it's parent's offset, then it's.
            // Subtract to find the element height.
            // Then, scroll to the top of the element.
            
            right=(document.getElementById('right')); 
            mytop = jQuery("#" + jumpto ).offset().top; 
            // if ( jQuery("#" + jumpto ).parent() )
            // {
            //     parenttop = jQuery("#" + jumpto ).parent().offset().top; 
            // }
            // else
            // {
            //     parenttop = jQuery("#" + jumpto ).offset().top; 
            // }
            // DivHeight = mytop - parenttop;
            right.scrollTop = mytop; // - DivHeight;   
        }
    }

jQuery('#spinner').html('<img src="/static/images/spinner.gif" height="31" width="31" alt=" ">');
    
});
