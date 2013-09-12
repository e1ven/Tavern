jQuery(document).ready(function () {
    jQuery(".messageform").submit(function(){
        showSpinner(this);
    });
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
                    jQuery('#progress_' + referenced_form ).html("Uploading complete.");

                });
                jQuery('.icon-upload').css('color','#000000');
                jQuery('.uploadbox').css('border-color','#000000');
            }
        });

    });


    // Set up our editor options-
    // First, the marked parser

    marked.setOptions({
      gfm: true,
      tables: false,
      breaks: true,
      pedantic: false,
      sanitize: true,
      smartLists: false,
      smartypants: false,
      langPrefix: 'lang-'
    });

    // Now, create an instance of the Epic Editor, sync it up with the Body textarea.
    var opts = {
      container: 'contenteditable',
      textarea: 'textareabody',
      basePath: '',
      clientSideStorage: false,
      useNativeFullscreen: true,
      parser: marked,
      theme: {
        base: '/static/css/editor-base.css',
        preview: '/static/css/editor-preview.css',
        editor: '/static/css/editor-edit.css'
      },
      button: {
        preview: true,
        fullscreen: true,
        bar: "auto"
      },
      autogrow: {
        minHeight: jQuery('#textareabody').height()
      },
      focusOnLoad: true,
      string: {
        togglePreview: 'Preview your message',
        toggleEdit: 'Return to editing your message',
        toggleFullscreen: 'Enter Fullscreen editing mode'
      }    
    }
    var editor = new EpicEditor(opts).load(
        function () {

            // Set the ContentEditable div to be the size/shape of our text-area above.
            textarea = jQuery('#textareabody');
            contenteditable = jQuery('#contenteditable');
            contenteditable.show();

            contenteditable.css({
              'width':textarea.width(),
              'height':textarea.height()
            });
            
            // Once the EpicEditor is loaded, hide the text area.
            // Do it here so that the textarea isn't hidden if we DON'T load successfully.
            textarea.hide();
        });
});
