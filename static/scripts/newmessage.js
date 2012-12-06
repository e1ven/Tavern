jQuery(document).ready(function () {
    jQuery("#dragdroptext").html("Drag and Drop or choose files to attach")
    jQuery(".hiddenupload").show();
    jQuery(".single_file_upload").hide();
    var referenced_files = 1;
    jQuery(function () {
        jQuery('.uploadfileform').fileupload({
            dataType: 'json',
            add: function (e, data) {
                referenced_form = jQuery(this).attr('references');
                data.submit();
            },
            progressall: function (e, data) {
                referenced_form = jQuery(this).attr('references');
                jQuery('#progress_' + referenced_form ).show();
                var progress = parseInt(data.loaded / data.total * 100, 10);
                jQuery('#progress_' + referenced_form ).html("Uploading :: " + progress + "% complete.");
            },
            done: function (e, data) {
                referenced_form = jQuery(this).attr('references');
                jQuery.each(data.result, function (index, file) {
                    jQuery("#filelist_" + referenced_form).append(file.name + "<br>");
                    //Add a hidden variable to the original form, so we know what we just spot-uploaded
                    jQuery("#" + referenced_form).append('<input type="hidden" name="referenced_file' + referenced_files + '_hash" value = "' + file.hash + '">')
                    jQuery("#" + referenced_form).append('<input type="hidden" name="referenced_file' + referenced_files + '_name" value = "' + file.name + '">')
                    jQuery("#" + referenced_form).append('<input type="hidden" name="referenced_file' + referenced_files + '_size" value = "' + file.size + '">')
                    jQuery("#" + referenced_form).append('<input type="hidden" name="referenced_file' + referenced_files + '_contenttype" value = "' + file.content_type + '">')
                    referenced_files +=1;
                });
                jQuery('.icon-upload').css('color','#000000');
                jQuery('.uploadbox').css('border-color','#000000');
            }
        });

    });
});
