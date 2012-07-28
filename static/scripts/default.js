
jQuery(document).ready(function() {
    $jQuery = jQuery.noConflict();

    if (jQuery("#centerandright").length)
    {

        // If we've saved any values to storage, retrieve them, and keep the page the size it was.

        left = jQuery.jStorage.get('#left.width','');
        centerandright = jQuery.jStorage.get('#centerandright.width','');
        center = jQuery.jStorage.get('#center.width','');
        right =  jQuery.jStorage.get('#right.width','');

        if (left + centerandright + center + right != '' )
        {
            jQuery('#left').css('width',left);
            jQuery('#centerantright').css('width',centerandright);
            jQuery('#center').css('width',center);
            jQuery('#right').css('width',right);

        }
        else
        {
            //default widths
            jQuery('#left').width(jQuery('#left').parent().parent().width() * .15)
            jQuery('#centerandright').width(jQuery('#centerandright').parent().parent().width() * .85)
            jQuery('#center').width(jQuery('#centerandright').width() * .25)
            jQuery('#right').width(jQuery('#centerandright').width() * .75)
        }
        
        // Now, do the splitting.
        VerticalSplitter.SetUpElement({ containerId: "content", firstItemId: "left", secondItemId: "centerandright" });
        VerticalSplitter.SetUpElement({ containerId: "centerandright", firstItemId: "center", secondItemId: "right" });
    }



    jQuery('.splitter').mouseup(function() {

        // On Mouseup, save the current position, so we can do new pages at the same place.

        jQuery.jStorage.set('#left.width',jQuery('#left').css('width'));
        jQuery.jStorage.set('#centerandright.width',jQuery('#centerandright').css('width'));
        jQuery.jStorage.set('#center.width',jQuery('#center').css('width'));
        jQuery.jStorage.set('#right.width',jQuery('#right').css('width'));

        // Redraw the splitter, so ensure that if we move Splitter 1 and push splitter2 offscreen, we still redraw it.

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
jQuery.getScript('/static/scripts/instance.js');
  
});
