      // Note the votes we've already cast
      // If we're doing this here, it's because we're in a browser that
      // doesn't support animation, so we can't use the insert fake animation hack.
      // Instead, loop through all elements.
      if (! detectAnimation())
      {
          jQuery(".vote").each( function ()
          {
              /* get some values from elements on the page: */
              var jQueryform = jQuery( this ),
                  rating = jQueryform.find( 'input[name="rating"]' ).val(),
                  url = jQueryform.attr( 'action' ),
                  hash = jQueryform.find( 'input[name="hash"]' ).val();

              /* Find the ones we've hit before */
              hashdata = jQuery.jStorage.get(hash,{});
              rating = hashdata['rating'];
              jQueryform.find( 'input[name="rating"][value=' + rating + ']' ).parent().css("border","1px solid #000000");

          });
      }

    // Ensure there is a checkbox, which looks nicer, in the JS version, rather than the textbutton.
    jQuery('.alwaysdisplay > .textbutton').hide();
    jQuery('.alwaysdisplay').append('<input type="checkbox" name="showembeds" value="True" class="checkalways" /> Always display external content <br />')



    // Notice if Pubkey has changed, and clear localstorage. Primarily used if we logout, etc.
    if (jQuery("#youravatar").length)
      youravatar = jQuery('#youravatar').attr('src');
    else 
      youravatar = 'NoAvatar';

    if (jQuery.jStorage.get('youravatar','NeverBeenSet') != youravatar )
    {
      jQuery.jStorage.flush();
      jQuery.jStorage.set('youravatar', youravatar); 
    }