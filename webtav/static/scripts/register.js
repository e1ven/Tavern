jQuery(document).ready(function() 
{




	// Calculate the domain they MIGHT have meant.
	jQuery('#email').on('blur', function() 
	{
	  Kicksend.mailcheck.run(
	  {
		  email: jQuery('#email').val(),
		  suggested: function(suggestion) 
		  {
		  	jQuery('#EmailStatus').html('<p><i>&nbsp;&nbsp;&nbsp; Did you mean '+suggestion.address+'@'+'<strong>'+suggestion.domain+'</strong>?</i></p>').show();

		    //Register a handler to hide this new suggestion.
		    jQuery('#EmailStatus').click(function(event) 
		    {
		    	jQuery('#email').val(suggestion.full);
		    	jQuery('#EmailStatus').hide();    
		    });
		   },
		    empty: function(element) 
		    {
			        jQuery('#EmailStatus').html('').hide();
		    }
	   });
	});



	jQuery('#pass').keyup(function() 
	{
		result = zxcvbn( this.value );
		pass1 = this.value
		PassDescriptions = ['Not Very Strong', 'Average', 'Good', 'Very Good', 'Great'];
		jQuery('#PasswordStatus').html("<p><i>&nbsp;&nbsp;&nbsp;Password Strength: " + PassDescriptions[result.score]) + "</i></p>";
	});
	jQuery('#pass2').keyup(function() 
	{
		if (this.value != pass1 )
		{
			jQuery('#PasswordStatus').html("<p><i>&nbsp;&nbsp;&nbsp;Passwords do not match</i></p>");
		}
		else
		{
			jQuery('#PasswordStatus').html("<p><i>&nbsp;&nbsp;&nbsp;Passwords match</i></p>");
		}
	});
});