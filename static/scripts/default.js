jQuery.ajaxSetup({
  //We're already adding a requests parameter, just like jQuery would.
  //We don't need both ;)
  cache: true
});



// Part of Fontello
function toggleCodes(on) {
  var obj = document.getElementById('icons');
  if (on) {
    obj.className += ' codesOn';
  } else {
    obj.className = obj.className.replace(' codesOn', '');
  }
}
    


// Detect if CSS Animation support is enabled.
// We're going to use this later to register events (quickly) on elements added after page load.
function detectAnimation()
{
    elm = document.documentElement;
    var animation = false,
        animationstring = 'animation',
        keyframeprefix = '',
        domPrefixes = 'Webkit Moz O ms Khtml'.split(' '),
        pfx  = '';
     
    if( elm.style.animationName ) { animation = true; }   
     
    if( animation === false ) {
      for( var i = 0; i < domPrefixes.length; i++ ) {
        if( elm.style[ domPrefixes[i] + 'AnimationName' ] !== undefined ) {
          pfx = domPrefixes[ i ];
          animationstring = pfx + 'Animation';
          keyframeprefix = '-' + pfx.toLowerCase() + '-';
          animation = true;
          break;
        }
      }
    }

    return animation
}


// Function to properly size the 3 column layout
function sizewindow()
{
  if (jQuery("#centerandright").length)
  {
    // Set content to position:absolute. Doing this in JS so it doesn't get set for JS disabled browsers. This helps for #single elements
    jQuery('#content').css('position','absolute');
    //Set the content window
    jQuery('#content').css('height', jQuery(window).height() - jQuery('header').height() - 50  );
  }
    // Set out footer position
    jQuery('#footer').offset({top:jQuery('#content').offset()['top'] + jQuery('#content').height() + 10});
    

  // Redraw the splitters, if there is content to split.
  if(typeof VerticalSplitter != 'undefined')
  {
    if (jQuery("#centerandright").length)
    {
      VerticalSplitter.SetUpElement({ containerId: "content", firstItemId: "left", secondItemId: "centerandright" });
    }
    if (jQuery("#centerandright").length)
    {
      VerticalSplitter.SetUpElement({ containerId: "centerandright", firstItemId: "center", secondItemId: "right" });
    }   
  } 
   
} 

// Throttled version of Resize
var throttledSizeWindow = jQuery.throttle(sizewindow, 200, null, true);

// Now, bind the throttled version to resize
jQuery(window).resize(function() {
  throttledSizeWindow();
});



// Set default positions for the various columns.
function ensureMinDivSizes(force)
{
  //default force to false
  force = typeof force !== 'undefined' ? force : false;

  if (jQuery('#left').width() < 50) or (force = true)
    jQuery('#left').width(jQuery('#left').parent().parent().width() * .15 );

  if (jQuery('#centerandright').width() < 100) or (force = true)
    jQuery('#centerandright').width(jQuery('#centerandright').parent().parent().width() * .85);

  if (jQuery('#center').width() < 50) or (force = true)
    jQuery('#center').width(jQuery('#centerandright').width() * .25);

  if (jQuery('#right').width() < 50) or (force = true)
    jQuery('#right').width(jQuery('#centerandright').width() * .75);
}

// Save the column positions.
function savedivsizes()
{
    jQuery.jStorage.set('#left.width',jQuery('#left').width() );
    jQuery.jStorage.set('#centerandright.width',jQuery('#centerandright').width() );
    jQuery.jStorage.set('#center.width',jQuery('#center').width() );
    jQuery.jStorage.set('#right.width',jQuery('#right').width() );
}

// Simple Util function. Useful!
function getParameterByName(name) {
   var match = RegExp('[?&]' + name + '=([^&]*)')
                   .exec(window.location.search);
   return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
}

// Our onLoads-
jQuery(document).ready(function() {

    // We're using jQuery(foo), rather than $(foo)
    // This is more clear, and works with other systems better.

    $jQuery = jQuery.noConflict();
    
    throttledSizeWindow();


    // Resize to saved div sizes
    // Doing this here, as opposed to in sizeWindow, so that it ONLY happens at page load.
    // No reason to be doing this over and over.

    if (jQuery("#centerandright").length)
      {
        // If we've saved any values to storage, retrieve them, and keep the page the size it was.
        left = jQuery.jStorage.get('#left.width',0);
        centerandright = jQuery.jStorage.get('#centerandright.width',0);
        center = jQuery.jStorage.get('#center.width',0);
        right =  jQuery.jStorage.get('#right.width',0);

        ensureMinDivSizes();
        
     };
 
    // Issue a resize if you slide the splitter
    jQuery(document).on("mouseup", ".splitter", function(event){
        // On Mouseup, save the current position, so we can do new pages at the same place.
        if ( (jQuery('#left').width() != jQuery.jStorage.get('#left.width','')) ||
             (jQuery('#centerandright').width() != jQuery.jStorage.get('#centerandright.width','')) ||
             (jQuery('#center').width() != jQuery.jStorage.get('#center.width','')) ||
             (jQuery('#right').width() != jQuery.jStorage.get('#right.width',''))      )
                {
                    // If we're here, we've moved the sliders, not just clicked on them.
                    savedivsizes();
                    // Redraw the splitter, so ensure that if we move Splitter 1 and push splitter2 offscreen, we still redraw it.
                    throttledSizeWindow();
               }
    });

    // If we pass a Jumpto param, scroll down.
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



    // Create a spinner in JS, so we don't see it with Lynx/etc.

    if ( detectAnimation() == true)
    {
      jQuery('#spinner').html('<img src="/static/images/spinner.gif" height="31" width="31" alt=" ">');
      jQuery('#spinner').html('<i class="icon-spin5 animate-spin"></i>');
    }
    else
    {
      jQuery('#spinner').html('<img src="/static/images/spinner.gif" height="31" width="31" alt=" ">');
    }
    // Place the spinner for all tagged links.
    jQuery(document).on('click','.internal',function(event)
        {
        event.preventDefault();
        jQuery('#spinner').show()
        jQuery("#spinner").height(jQuery(this).parent().height());
        jQuery("#spinner").width(jQuery(this).parent().width());
        jQuery("#spinner").css("top", jQuery(this).parent().offset().top).css("left", jQuery(this).parent().offset().left).show();
        if (jQuery(this).attr('href').indexOf('?') == -1 )
          urlsep = '?';
        else
          urlsep = '&';
        jQuery.getScript( jQuery(this).attr('href') + urlsep + "js=yes&timestamp=" + Math.round(new Date().getTime())  );
        });

    // Send notes via Ajax
    jQuery(document).on("submit", ".usernote", function(event) {
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


    // Send votes via Ajax.
    jQuery(document).on("submit",".vote", function(event) {
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



    // Send FollowTopic via AJAX
    jQuery(document).on("submit",".followtopic", function(event) {
        ref = jQuery(this);
        /* stop form from submitting normally */
        event.preventDefault();

        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            url = jQueryform.attr( 'action' );

        ref.children().hide();
        ref.append('One moment please..');
        /* Send the data using post and put the results in a div */
        jQuery.post( url, {'_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(),'topic' : jQueryform.find( 'input[name="topic"]' ).val() },
          function( data ) {
              ref.empty().append("All set.");
              jQuery.getScript('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );
          }
        );

    });


    // Send Followuser via AJAX
    jQuery(document).on('submit','.followuser', function(event) {
        ref = jQuery(this);
        /* stop form from submitting normally */
        event.preventDefault();

        /* get some values from elements on the page: */
        var jQueryform = jQuery( this ),
            url = jQueryform.attr( 'action' );
        ref.children().hide();
        ref.append('One moment please..');
        /* Send the data using post and put the results in a div */
        jQuery.post( url, {'_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(),'pubkey' : jQueryform.find( 'input[name="pubkey"]' ).val() },
          function( data ) {
              ref.empty().append("All set.");
              jQuery.getScript('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );
          }
        );

    });


    // Pull in the reply box
    jQuery(document).on('click','.reply',function(event) {
        event.preventDefault();
        var jQuerymsg = jQuery(this).attr('message');
        var jQueryhref = jQuery(this).attr('href');
        jQuery.get(jQueryhref + "?getonly=true",function(data) {
          jQuery('#reply_'+jQuerymsg).html(data);
        });   
        
    });  



    // Pop up a box when they click on a user avatar
    jQuery(document).on('click','a.details',function(event)
    { 
          //TODO - This is firing twice. The stop propogation fixes.. But why?   
          event.stopImmediatePropagation();

          userdiv = "details_" + jQuery(this).attr('user');
          avatar = jQuery("#avatar_" + jQuery(this).attr('user'));
          jQuery("#" + userdiv).click(function()
          { // hide on clicks to the function itself.
      //      jQuery(this).hide();
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

    // Hide any linked content by default.
    // Don't even LOAD it. Just know where it is.
    // If they click to load, then adjust the page to retrieve
    jQuery(document).on('click','.embeddedcontentnote',function (event)
    {   
        var embededcontent = jQuery(event.target).next(); 
        if (embededcontent.is(":visible"))
        {
            embededcontent.hide();
        }
        else
        {
            embededcontent.show();
            embededcontent.prepend(embededcontent.attr('stufftoshow') + "<br>");
        }
    });

    // If you do click on the 'AlwaysShow external content
    // Save it, then make it take effect now.
    jQuery(document).on('click','.checkalways',function(event)
    {
        var displayform = jQuery( event.target ).parent();         
        url = displayform.attr( 'action' );
        displayform.hide();
        jQuery.post( url + '/ajax', { 'value': displayform.find( 'input[name="showembeds"]' ).val(),'_xsrf' : displayform.find( 'input[name="_xsrf"]' ).val()},                  
            function( data ) 
                  {
                     displayform.html( data );
                     displayform.show();
                  });
        // If you clicked it, show all the media on THIS page, too.
        // It's the little stuff, you know?
        jQuery('.embeddedcontentnote').each( function ()
          {
              var embededcontent = jQuery(this).next(); 
              embededcontent.show();
              embededcontent.html(embededcontent.attr('stufftoshow') + "<br>");
          });
        jQuery('.icon-picture').hide();
    });


    // If you do click on the 'AlwaysShow external content
    // Save it, then make it take effect now.
    jQuery(document).on('dblclick','.splitter',function(event)
    {
        //Force the default size;
        ensureMinDivSizes(true);
        throttledSizeWindow();
        savedivsizes();
    });

    // Bind key Events.
    // This should probably be broken out into it's own file.
    // For now, leave it here - This is just a sample key event, to verify the handler works.
    // Add more later.
    Mousetrap.bind('up up', function() {
        element = jQuery('#top');
        element.css('-moz-transform', 'rotate(180deg)'); 
        element.css('-o-transform','rotate(180deg)');  
        element.css('-webkit-transform','rotate(180deg)'); 
        element.css('-ms-transform','rotate(180deg)'); 
        element.css('transform','rotate(180deg);'); 
        element.css('filter','progid:DXImageTransform.Microsoft.Matrix(M11=-1, M12=-1.2246063538223773e-16, M21=1.2246063538223773e-16, M22=-1, sizingMethod="auto expand")');
    });









// Run the per-instance stuff.
jQuery.getScript('/static/scripts/instance.min.js');


    // Mark all the votes we've already cast.
    // Thanks http://www.backalleycoder.com/2012/04/25/i-want-a-damnodeinserted/
    // You deserve some gold bullion.
    // Do this AFTER the instance script, so that the jStorage settings are already set/cleared.

    if (detectAnimation())
    {
        jQuery(document).on("animationstart",".vote",function(event)
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

});