
    jQuery('a.internal').each( function ()
    {            
        jQuery(this).click(function()
            {   
            jQuery("#spinner").height(jQuery(this).parent().height());
            jQuery("#spinner").width(jQuery(this).parent().width());
            jQuery("#spinner").css("top", jQuery(this).parent().offset().top).css("left", jQuery(this).parent().offset().left).show()
            jQuery.getScript(jQuery(this).attr('link-destination') + "?js=yes&timestamp=" + Math.round(new Date().getTime())  );            
            return false;
            });
        jQuery(this).attr("link-destination",this.href);
    });
    jQuery('#spinner').hide();

    jQuery(".usernote").submit(function(event) {
        /* stop form from submitting normally */
        noteref = jQuery(this);
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            rating = jQueryform.find( 'input[name="rating"]' ).val(),
            url = jQueryform.attr( 'action' );

        /* Send the data using post and put the results in a div */
        jQuery.post( url, { 'pubkey': jQueryform.find( 'input[name="pubkey"]' ).val(),
                       '_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(), 
                       'note' : jQueryform.find( 'input[name="note"]' ).val() },
          function( data ) {
              noteref.empty().append( data );
          }
        );
    });        

     jQuery(".vote").submit(function(event) {
        voteref = jQuery(this);
        /* stop form from submitting normally */
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            rating = jQueryform.find( 'input[name="rating"]' ).val(),
            url = jQueryform.attr( 'action' ),
            hash = jQueryform.find( 'input[name="hash"]' ).val();

              rating = jQueryform.find( 'input[name="rating"]' ).val(),
              hashdata = jQuery.jStorage.get(hash,{});
              hashdata['rating'] = rating;
              jQuery.jStorage.set(hash, hashdata);   

              /* Mark the vote as selected, unselect the other vote */
              jQueryform.find( 'input[name="rating"][value=' + rating + ']' ).parent().css("border","1px solid #000000");
              jQueryform.find( 'input[name="rating"][value=' + rating + ']' ).parent().parent().find('input[name="rating"][value=' + rating * -1 + ']').parent().css("border","1px solid #dddddd");

              
        /* Send the data using post and put the results in a div */
        jQuery.post( url, { 'rating': jQueryform.find( 'input[name="rating"]' ).val(),
                       '_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(), 
                       'hash' : jQueryform.find( 'input[name="hash"]' ).val() });
    });                
    

    /* Note the votes we've already cast */
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


    jQuery(".followtopic").submit(function(event) {
        ref = jQuery(this);
        /* stop form from submitting normally */
        event.preventDefault(); 

        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            url = jQueryform.attr( 'action' );

        ref.children().hide()
        ref.append('One moment please..')
        /* Send the data using post and put the results in a div */
        jQuery.post( url, {'_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(),'topic' : jQueryform.find( 'input[name="topic"]' ).val() },
          function( data ) {
              ref.empty().append("All set.");
              jQuery.getScript('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );            
          }
        );

    });


    jQuery(".followuser").submit(function(event) {
        ref = jQuery(this);
        /* stop form from submitting normally */
        event.preventDefault(); 

        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            url = jQueryform.attr( 'action' );
        ref.children().hide()
        ref.append('One moment please..')
        /* Send the data using post and put the results in a div */
        jQuery.post( url, {'_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(),'pubkey' : jQueryform.find( 'input[name="pubkey"]' ).val() },
          function( data ) {
              ref.empty().append("All set.");
              jQuery.getScript('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );            
          }
        );

    });


    jQuery(".reply").click(function(event) {
        event.preventDefault();
        var jQuerymsg = jQuery(this).attr('message');
        var jQueryhref = jQuery(this).attr('href');
        jQuery.get(jQueryhref + "?getonly=true",function(data) {
          jQuery('#reply_'+jQuerymsg).html(data);
        });   
        
    });  


    jQuery('a.details').each( function ()
    {            
        jQuery(this).click(function()
            {   
              userdiv = "details_" + jQuery(this).attr('user');
              avatar = jQuery("#avatar_" + jQuery(this).attr('user'));

              jQuery("#" + userdiv).click(function()
              { // hide on clicks to the function itself.
                jQuery(this).hide();
              });

              if (jQuery("#" + userdiv).is(":visible"))
              {
                  jQuery("#" + userdiv).hide();
              }
              else
              {
                  jQuery("#" + userdiv).show();
                  // Stupid WebKit workaround. - Webkit isn't pulling position on the Avatar correctly, so pull from the grandparent, then adjust
                  pos = avatar.parent().parent().position();
                  pos.left += avatar.width();

                  if (jQuery(this).attr('orient') == "left")
                  {
                    jQuery("#" + userdiv).css({top: pos.top + avatar.height(), left: pos.left - avatar.width(), position: 'absolute'});
                  }
                  else
                  {
                    jQuery("#" + userdiv).css({top: pos.top + avatar.height(), right: pos.right, position: 'absolute'});
                  }
              }
              return false;
            });
    });

    // Hide any linked content by default.
    // Don't even LOAD it. Just know where it is.
    // If they click to load, then adjust the page to retrieve
    jQuery('.embeddedcontentnote').each( function ()
    {           
        var embededcontent = jQuery(this).next(); 
        jQuery(this).click(function()
            {  
              if (embededcontent.is(":visible"))
              {
                  embededcontent.hide();
              }
              else
              {
                  embededcontent.show();
                  embededcontent.prepend(embededcontent.attr('stufftoshow') + "<br>");
              }
            })
    });


    // Ensure there is a checkbox, which looks nicer, in the JS version, rather than the textbutton.
    jQuery('.alwaysdisplay > .textbutton').hide();
    jQuery('.alwaysdisplay').append('<input type="checkbox" name="showembeds" value="True" class="checkalways" /> Always display external content <br />')

    jQuery('.checkalways').click( function(e){
        var displayform = jQuery( this ).parent();         
        url = displayform.attr( 'action' );
        displayform.hide();
        jQuery.post( url + '/ajax', { 'value': displayform.find( 'input[name="showembeds"]' ).val(),'_xsrf' : displayform.find( 'input[name="_xsrf"]' ).val()},                  
            function( data ) 
                  {
                     displayform.empty().append( data );
                     displayform.show();
                  });
        // If you clicked it, show all the media on THIS page, too.
        // It's the little stuff, you know?
        jQuery('.embeddedcontentnote').each( function ()
          {
              var embededcontent = jQuery(this).next(); 
              embededcontent.show();
              embededcontent.empty().append(embededcontent.attr('stufftoshow') + "<br>");
          });
        jQuery('.icon-picture').hide();

    });

// Set out footer size.
function sizewindow()
{
  if (! jQuery('.single').length)
  {
    // Set content to position:absolute. Doing this in JS so it doesn't get set for JS disabled browsers. This helps for #single elements
    jQuery('#content').css('position','absolute');
    //Set the content window
    jQuery('#content').css('height', jQuery(window).height() - jQuery('header').height() - 50  );
  }
    // Set out footer position
    jQuery('#footer').offset({top:jQuery('#content').offset()['top'] + jQuery('#content').height() + 10});
} 

jQuery(document).ready(function() {
  sizewindow()
});

jQuery(window).on('resize',function() {
  sizewindow()
});
