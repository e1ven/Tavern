jQuery(document).ready(function() {
	jQuery('#email').blur(function() {
	    jQuery(this).mailcheck({
	      suggested: function(element, suggestion) {
	        jQuery('#EmailStatus').html('<p><i>&nbsp;&nbsp;&nbsp; Did you mean '+suggestion.address+'@'+'<strong>'+suggestion.domain+'</strong>?</i></p>').show();

	        jQuery('#EmailStatus').click(function(event) {
	        	jQuery('#email').val(suggestion.full);
	        	jQuery('#EmailStatus').hide();
	        });
	      

	      },
	      empty: function(element) {
	        jQuery('#EmailStatus').html('').hide();
	      }
	    });
	});


	jQuery('#pass').keyup(function() {
		result = zxcvbn( this.value );
		pass1 = this.value
		PassDescriptions = ['Not Very Strong', 'Average', 'Good', 'Very Good', 'Great'];
		jQuery('#PasswordStatus').html("<p><i>&nbsp;&nbsp;&nbsp;Password Strength: " + PassDescriptions[result.score]) + "</i></p>";
	});
	jQuery('#pass2').keyup(function() {
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

