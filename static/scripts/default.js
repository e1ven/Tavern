jQuery.ajaxSetup({
  //We're already adding a requests parameter, just like jQuery would.
  //We don't need both ;)
  cache: true
});


// Strip a trailing slash from a URL if there is one.
function stripTrailingSlash(str) {
    if(str.substr(-1) == '/') {
        return str.substr(0, str.length - 1);
    }
    return str;
}


function removeParameter(url, parameter)
{
  var urlparts= url.split('?');

  if (urlparts.length>=2)
  {
      var urlBase=urlparts.shift(); //get first part, and remove from array
      var queryString=urlparts.join("?"); //join it back up

      var prefix = encodeURIComponent(parameter)+'=';
      var pars = queryString.split(/[&;]/g);
      for (var i= pars.length; i-->0;)               //reverse iteration as may be destructive
          if (pars[i].lastIndexOf(prefix, 0)!==-1)   //idiom for string.startsWith
              pars.splice(i, 1);
      url = urlBase+'?'+pars.join('&');
  }
  return url;
}


// Slider function which executes when sliding the column slider
function onSlide(e){
    var columns = jQuery(e.currentTarget).find("td");
    var ranges = [], total = 0, i, s ="Ranges: ", w;
    for(i = 0; i<columns.length; i++){
        w = columns.eq(i).width()-14 - (i==0?1:0);
        ranges.push(w);
        total+=w;
    }    
    for(i=0; i<columns.length; i++){      
        ranges[i] = 100*ranges[i]/total;            
    }   
    s=s.slice(0,-1);      
    jQuery("#sliderResults").html(" Percent selected : "+ Math.round(ranges[0]*10)/10 +"%");
}



// Bind the slider javascript to the comment parser
// Since this doesn't like to rebind to the same ID
// We're generating a random name for each one in the Python code.
function setupColumnSlider(jqueryobj)
{
    jqueryobj.colResizable({
      liveDrag:true, 
      draggingClass:"commentSliderDrag", 
      gripInnerHtml:"<div class='commentSliderGrip'></div>", 
      onResize:onSlide,
      minWidth:0
    });
}

// Send votes via Ajax.
function setupVotes(jqueryobj)
{
    jQuery(jqueryobj).one("submit", function(event) {
        voteref = jQuery(this);
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        jQueryform = jQuery( this );
        rating = jQueryform.find( 'input[name="rating"]' ).val();
        url = jQueryform.attr( 'action' );
        hash = jQueryform.find( 'input[name="hash"]' ).val();
        rating = jQueryform.find( 'input[name="rating"]' ).val(),
        hashdata = jQuery.jStorage.get(hash,{});
        hashdata['rating'] = rating;
        jQuery.jStorage.set(hash, hashdata);   

        // Mark it as voted
        jQueryform.find( 'input[name="rating"][value=' + rating + ']' ).parent().addClass("darkClass");


        /* Send the data using post and put the results in a div */
        jQuery.post( url, { 'rating': jQueryform.find( 'input[name="rating"]' ).val(),
                       '_xsrf' : jQueryform.find( 'input[name="_xsrf"]' ).val(), 
                       'hash' : jQueryform.find( 'input[name="hash"]' ).val() });
    });                
}

// Pull in the reply box inline
function setupReplies(jqueryobj)
{
    jQuery(jqueryobj).one('click',function(event) {
        event.preventDefault();
        var jQuerymsg = jQuery(this).attr('message');
        var jQueryhref = jQuery(this).attr('href');
        jQuery.get(jQueryhref + "?getonly=replywrapper",function(data) {
          jQuery('#reply_'+jQuerymsg).html(data);
        });   
        
    });  
}


// Override the click on .internal to load them via JS instead.
function setupInternalLinks(jqueryobj)
{
    // Place the spinner for all tagged links.
    jQuery(jqueryobj).one('click',function(event)
        {

        // Don't fire off more than once.
        event.preventDefault();
        event.stopImmediatePropagation();
        
        // set the main spinner block, including the dimming
        jQuery('#spinner').show()
        jQuery("#spinner").height(jQuery(this).parent().height());
        jQuery("#spinner").width(jQuery(this).parent().width());
        jQuery("#spinner").css("top", jQuery(this).parent().offset().top).css("left", jQuery(this).parent().offset().left).show();
        jQuery(".spinnerimg").css("height","95%");

        if (jQuery(this).attr('href').indexOf('?') == -1 )
          urlsep = '?';
        else
          urlsep = '&';
        jQuery.getScript( jQuery(this).attr('href') + urlsep + "js=yes&timestamp=" + Math.round(new Date().getTime())  );
        });
}

// Submit UserNotes via Ajax
function setupNotes(jqueryobj)
{
    jQuery(jqueryobj).one("submit", function(event) {
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
}

// If you do click on the 'AlwaysShow external content
// Save it, then make it take effect now.
function setupAlwaysCheck(jqueryobj)
{
    jQuery(jqueryobj).one('click',function(event)
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
}

function setupFollowTopic(jqueryobj)
{
    // Send FollowTopic via AJAX
    jQuery(jqueryobj).one("submit", function(event) {
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
              jQuery.getScript(stripTrailingSlash(document.URL) + '/?js=yes&divs=savedtopics,followtopic' + "&timestamp=" + Math.round(new Date().getTime())  );
          }
        );

    });
}

// Hide any linked content by default.
// Don't even LOAD it. Just know where it is.
// If they click to load, then adjust the page to retrieve
function setupEmbeddedNote(jqueryobj)
{
    jQuery(jqueryobj).one('click',function (event)
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
}


// Pop up a box when they click on a user avatar
function setupUserDetails(jqueryobj)
{
    jQuery(jqueryobj).one('click',function(event)
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
}

// Pop up a box when they click on a user avatar
function setupFollowUser(jqueryobj)
{

   // Send Followuser via AJAX
    jQuery(jqueryobj).one('submit', function(event) {
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
              jQuery.getScript(stripTrailingSlash(document.URL) +'/?js=yes&divs=column1,followuser' + "&timestamp=" + Math.round(new Date().getTime())  );
          }
        );

    });
}



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
    return animation;
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

    // Make the main layout table resizable
    jQuery("#wrappertable").colResizable(
    {
      liveDrag:true,
      postbackSafe: true
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
      var opts = {
        lines: 13, // The number of lines to draw
        length: 7, // The length of each line
        width: 4, // The line thickness
        radius: 8, // The radius of the inner circle
        corners: 1, // Corner roundness (0..1)
        rotate: 0, // The rotation offset
        color: '#000', // #rgb or #rrggbb
        speed: 1, // Rounds per second
        trail: 60, // Afterglow percentage
        shadow: false, // Whether to render a shadow
        hwaccel: true, // Whether to use hardware acceleration
        className: 'spinnerimg', // The CSS class to assign to the spinner
        zIndex: 1002, // The z-index (defaults to 2000000000)
        top: '0px', // Top position relative to parent in px
        left: '90%' // Left position relative to parent in px
      };
      var spinner = new Spinner(opts).spin();
      jQuery("#spinner").html(spinner.el);
    }
    else
    {
      jQuery('#spinner').html('<img class="spinnerimg" src="/static/images/spinner.gif" height="31" width="31" alt=" ">');
    }


    // Setup the various hooks on repeating
    // Note - We're going to do these again in the animation section, for the reloads.
    setupColumnSlider(jQuery(".commentSlider"));
    setupReplies(jQuery(".reply"));
    setupVotes(jQuery(".vote"));
    setupInternalLinks(jQuery(".internal"));
    setupNotes(jQuery(".usernote"));
    setupAlwaysCheck(jQuery(".checkalways"));
    setupFollowTopic(jQuery(".followtopic"));
    setupEmbeddedNote(jQuery(".embeddedcontentnote"));
    setupUserDetails(jQuery("a.details"));
    setupFollowUser(jQuery(".followuser"));

 

    // Bind key Events.
    // This should probably be broken out into it's own file.
    // For now, leave it here - This is just a sample key event, to verify the handler works.
    // Add more later.
    Mousetrap.bind('up up', function() {
        alert("upup");
        element = jQuery('#logo');
        element.css('-moz-transform', 'rotate(180deg)'); 
        element.css('-o-transform','rotate(180deg)');  
        element.css('-webkit-transform','rotate(180deg)'); 
        element.css('-ms-transform','rotate(180deg)'); 
        element.css('transform','rotate(180deg);'); 
        element.css('filter','progid:DXImageTransform.Microsoft.Matrix(M11=-1, M12=-1.2246063538223773e-16, M21=1.2246063538223773e-16, M22=-1, sizingMethod="auto expand")');
    });


    // Built the Javascript accordian menu.

    // Hide the sub-elements via JAVASCRIPT, so they are there if JS is disabled.
    jQuery(".accordion li > .sub-element").css("display","none");

    // Store variables
    var accordion_head = jQuery('.accordion > li > a'),
        accordion_body = jQuery('.accordion li > .sub-element');

    // Open the first tab on load
    // accordion_head.first().addClass('active').next().slideDown('normal');


    // Click function
    accordion_head.on('click', function(event) {
        // Disable header links
        event.preventDefault();
        // Show and hide the tabs on click

        if (jQuery(this).attr('class') != 'active')
        {
            accordion_body.slideUp('normal');
            jQuery(this).next().stop(true,true).slideToggle('normal');
            accordion_head.removeClass('active');
            jQuery(this).addClass('active');
        }
    });



    // Run the per-instance stuff.
    jQuery.getScript('/static/scripts/instance.min.js');

    // Run the things that need to execute on dynamically added elements.
    // See -  http://www.backalleycoder.com/2012/04/25/i-want-a-damnodeinserted/ for why it works.
    if (detectAnimation())
    {
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".followuser",function(event)
        {
            setupFollowUser(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart","a.details",function(event)
        {
            setupUserDetails(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".embeddedcontentnote",function(event)
        {
            setupEmbeddedNote(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".followtopic",function(event)
        {   
            setupFollowTopic(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".checkalways",function(event)
        {
            setupAlwaysCheck(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".usernote",function(event)
        {
            setupNotes(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".internal",function(event)
        {
            setupInternalLinks(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".reply",function(event)
        {
            setupReplies(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".vote",function(event)
        {
            setupVotes(jQuery(this));
        });
        jQuery(document).on("animationstart MSAnimationStart webkitAnimationStart",".commentSlider",function(event)
        {
            setupColumnSlider(jQuery(this));
        });
    }

});