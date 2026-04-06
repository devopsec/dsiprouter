;(function(window, document) {
  'use strict';

  // throw an error if required functions not defined
  if (typeof validateFields === "undefined") {
    throw new Error("validateFields() is required and is not defined");
  }
  if (typeof showNotification === "undefined") {
    throw new Error("showNotification() is required and is not defined");
  }
  if (typeof toggleElemDisabled === "undefined") {
    throw new Error("toggleElemDisabled() is required and is not defined");
  }

  // throw an error if required globals not defined
  if (typeof API_BASE_URL === "undefined") {
    throw new Error("API_BASE_URL is required and is not defined");
  }

	var ENTITY="agents";
  var id;
	var table;


  function clear(modal_selector) {
    /** Clear out the modal */
    var modal_body = $(modal_selector).find('.modal-body');

    var btn;
    if (modal_selector == "#add") {
      btn = $('#add .modal-footer').find('#addButton');
      btn.html("<span class='glyphicon glyphicon-ok-sign'></span> Add");
      btn.removeClass("btn-success");
      btn.addClass("btn-primary");
      modal_body.find('#domain').val("");
    }
    else {
      btn = $('#edit .modal-footer').find('#updateButton');
      btn.html("<span class='glyphicon glyphicon-ok-sign'></span> Update");
      btn.removeClass("btn-success");
      btn.addClass("btn-warning");
    }
    btn.attr('disabled', false);

  }

	function addEntity(action) {
		var selector, modal_body, url
		var requestPayload = {};
		
    url = CUSTOM_MODULE_API_BASE_URL + "agents/v1/agent";


		// The default action is a POST
		if (typeof action === "undefined") {
			action = "POST";
		}

		if (action === "POST") {
			action = "POST";
			selector = "#add";
			modal_body = $(selector + ' .modal-body');
      //requestPayload.domain = modal_body.find("#domain").val()

		}
    else if (action === "PUT") {
			action = "PUT";
			selector = "#edit";
			modal_body = $(selector + ' .modal-body');
      requestPayload.domain = modal_body.find("#domain2").val()

		}

    var requestPayload = {};
    requestPayload.type= modal_body.find("select#agent_type").val();
    requestPayload.project_id = modal_body.find("select#project_id").val();
    requestPayload.name = modal_body.find("input#agent_name").val();
    requestPayload.tools = modal_body.find("select#toolchain").val();
    requestPayload.callback_email = modal_body.find("input#callback_email").val();
    requestPayload.instructions = modal_body.find("textarea#agent_instructions").val();
    
    


    // Put into JSON Message and send over
    $.ajax({
      type: action,
      url: url,
      dataType: "json",
      contentType: "application/json; charset=utf-8",
      data: JSON.stringify(requestPayload),
      success: function(response, textStatus, jqXHR) {
        var btn;

        // Update the Add Button and the table
        if (action === "POST") {
          btn = $('#add .modal-footer').find('#addButton');
          btn.removeClass("btn-primary");
        }
        else {
          btn = $('#edit .modal-footer').find('#updateButton');
          btn.removeClass("btn-warning");
        }

        btn.addClass("btn-success");
        btn.html("<span class='glyphicon glyphicon-check'></span> Saved!");
        btn.attr("disabled", true);

        // Update Reload buttons if the number was assigned
        if(requestPayload.status === "assigned") {
          reloadKamRequired(true);
        }

        if (action === "POST") {
          agents_table.row.add({
            "id": response.data[0].id,
            "name": requestPayload.agent_name,
            "type": requestPayload.agent_type,
            "status": response.data[0].status,
            "did-mappings": response.data[0].did-mappings
          }).draw();

          // Clear the form fields for next entry
           clearFormFields("#add");
        }
         
        else {
          agents_table.row(function(idx, data, node) {
            return data.id === response.data[0].id;
          }).data({
            "id": response.data[0].id,
            "name": requestPayload.agent_name,
            "type": requestPayload.agent_type,
            "status": response.data[0].status,
            "did-mappings": response.data[0].did-mappings
          }).draw();
        }

       

      },
      error: function(jqXHR, textStatus, errorThrown) {
        var responseText = jQuery.parseJSON(jqXHR.responseText);
        if (action === "POST") {
          var messageText = "Add Failed: " + responseText["msg"];
        }
        else {
          var messageText = "Update Failed: " + responseText["msg"];
        } 
        showNotification(messageText, true);
      }
    });

}


function deleteEntity() {
    var id_int = parseInt(id, 10);

    $.ajax({
      type: "DELETE",
      url: API_BASE_URL + ENTITY + "/" + id,
      dataType: "json",
      contentType: "application/json; charset=utf-8",
      success: function(response, textStatus, jqXHR) {
        $('#delete').modal('hide');
        $('#edit').modal('hide');
        table.row(function (idx, data, node) {
            //return data.id === id_int;
            return data.domain === id;
        }).remove().draw();

        showNotification("Certificate was deleted");
      }
    });
  }

	$(document).ready(function() {

  
    var url = CUSTOM_MODULE_API_BASE_URL + "agents/v1/agent";

		// datatable init
		table = $('#' + ENTITY + "_table").DataTable({
			"ajax": {
				"url": url
			},
			"columns": [
				{"data": "id"},
				{"data": "name"},
				{"data": "type"},
				{"data": null, render: function(data, type, row) {
          if (data.status === "0") {
            return "Stopped <button class='btn btn-success btn-xs agent_stopped'><span class='glyphicon glyphicon-play'></span></button>";
          }
          else if (data.status === "1") {
            return "Started <button class='btn btn-warning btn-xs agent_started'><span class='glyphicon glyphicon-stop'></span></button>";
          }
         }
        },
        {"data": "did_mapping"},
			],
			"order": [[1, 'asc']]
		});

		// table editing by clicking on the row
		$('#' + ENTITY + ' tbody').on('click', 'tr', function() {
			//Turn off selected on any other rows
			$('#' + ENTITY).find('tr').removeClass('selected');

			if ($(this).hasClass('selected')) {
				$(this).removeClass('selected');
			}
			else {
				//table.$('tr.selected').removeClass('selected');
				$(this).addClass('selected');
				id = $(this).find('td').eq(1).text()
				if (id != "") {
				      $('#edit').modal('show');
      }
			}
		});


  /*  fetch('/api/agents/v1/instructions')
      .then(response => response.json())
     .then(results => {
        var instructions_select = document.querySelector(".predefined_instructions");
        instructions_select.innerHTML = "<option value=''>Select Instruction Set</option>";
        results.data.forEach(instruction_set => {
          var option = document.createElement("option");
          option.value = instruction_set.id;
          option.textContent = instruction_set.name + " - " + instruction_set.id;
          instructions_select.appendChild(option);
        });
    })
*/

$('.predefined_instructions').change(function() {

  var instruction_id = $(this).val();
  if (instruction_id) {
    fetch('/api/agents/v1/instructions/' + instruction_id)
      .then(response => response.json())
      .then(result => {
        $(".agent_instructions").val(result.data[0].instructions);
      })
  }
  else {
    $(".agent_instructions").val("");
  }

})


$('#open-Add').click(function() {
      clear('#add');
});

/* validate fields before submitting api request */
$('#addButton').click(function() {
		if (validateFields('#add')) {
			addEntity('POST');
      clear('#add_webhook_info');
      $('#add_webhook_info').dialog('open');

		}
});

$('#updateButton').click(function() {
		if (validateFields('#edit')) {
			addEntity('PUT');
		}
});

/* handler for deleting endpoint group */
$('#deleteButton').click(function() {
  deleteEntity();
});






$('#add').on('show.bs.modal', function() {
	
	$("#replace_default_cert").attr('checked',true);
	$("#replace_default_cert").trigger("change");
	$("#certtype_upload").trigger("change");
})


$('#edit').on('show.bs.modal', function() {
  clear('#edit');

  // Show the auth tab by default when the modal shows
  var modal_body = $('#edit .modal-body');

  // Put into JSON Message and send over
  $.ajax({
    type: "GET",
    url: API_BASE_URL + ENTITY + "/" + id,
    dataType: "json",
    contentType: "application/json; charset=utf-8",
    success: function(response, textStatus, jqXHR) {

      modal_body.find("#domain2").val(response.data[0].domain)
      if (response.data[0].type == "generated") {
        modal_body.find("#certtype_generate2").prop('checked', true);
      }
      else if (response.data[0].type == "uploaded") {
        modal_body.find("#certtype_upload2").prop('checked', true);
        $("#uploaded2").removeClass("hide");

      }
    },
      error: function(response, text_status, error_msg) {
        showNotification("Could not obtain certificate", true);
      }
  })
});

$(document).ajaxStart(function(){
  // Show image container
  $("#loader").show();
});
$(document).ajaxComplete(function(){
  // Hide image container
  $("#loader").hide();

});

$(".close").click(function () {

	document.getElementById("domain").value = "";
	$("#terminalDiv").addClass("hide");
	$("#terminalCommand").text("");
	$("#certtype_generate").prop('selected', true);
})

$(".agent_type").change(function () {

  if ($(".agent_type").val() == "openai") {

    // Get List of Projects for the provider and populate the project_id dropdown
      fetch('/api/agents/v1/projects/' + $(".agent_type").val())
        .then(response => response.json())
        .then(results => {
          var project_select = document.querySelector(".project_id");
          project_select.innerHTML = "<option value=''>Select Project ID</option>";
          results.data.forEach(project => {
            var option = document.createElement("option");
            option.value = project.id;
            option.textContent = project.name + " - " + project.id;
            project_select.appendChild(option);
          });
    })
  }
  else {
    var project_select = document.querySelector(".project_id");
    project_select.innerHTML = "<option value=''>Select Project ID</option>";
  } 

})

$(".project_id").change(function () {

  $(".agent_name").val($(".project_id").find("option:selected").text() + " " + "agent");

});


});

})(window, document);
