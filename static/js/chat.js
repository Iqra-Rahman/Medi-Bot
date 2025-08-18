$(document).ready(function() {

    // --- Core UI Functions ---
    function showToast(message, type = 'success') {
        const toast = $('#toast');
        toast.text(message);
        toast.removeClass('toast-success toast-error').addClass(type === 'success' ? 'toast-success' : 'toast-error');
        toast.addClass('toast-show');
        setTimeout(() => { toast.removeClass('toast-show'); }, 3000);
    }

    function setLoading(isLoading, btn = $('#form-submit-btn')) {
        const fieldset = $('#appointment-form fieldset');
        if (isLoading) {
            btn.addClass('btn-loading');
            fieldset.prop('disabled', true);
        } else {
            btn.removeClass('btn-loading');
            fieldset.prop('disabled', false);
        }
    }

    function resetForm() {
        $('#form-title').text('Book an Appointment');
        const btn = $('#form-submit-btn');
        btn.html('<span class="spinner"></span><span class="btn-text"><i class="fas fa-check"></i> Confirm Booking</span>');
        btn.removeClass('btn-warning').addClass('btn-primary');
        $('#appointment-form')[0].reset();
        $('#appointment-id').val('');
        $('#cancel-edit-btn').hide();
        $('#appointments-list').find('.is-editing').removeClass('is-editing');
    }

    // --- Data & AJAX Functions ---
    function refreshAppointments() {
        $.ajax({
            type: 'GET', url: '/appointments',
            success: function(data) {
                $('#appointments-list').html(data);
            },
            error: function() { showToast('Error refreshing appointments.', 'error'); }
        });
    }

    // --- Event Handlers ---

    // ## NEW: View Switching Logic ##
    $('.nav-btn').on('click', function() {
        const viewId = $(this).data('view');
        $('.nav-btn').removeClass('active');
        $(this).addClass('active');
        $('.view-pane').removeClass('active');
        $('#' + viewId).addClass('active');
    });

    $('#appointment-form').on('submit', function(e) {
        e.preventDefault();
        setLoading(true);

        const appointmentDateStr = $('#appointment-date').val();
        const appointmentTimeStr = $('#appointment-time').val();

        if (!appointmentDateStr || !appointmentTimeStr) {
            showToast('Please select both a date and a time.', 'error'); setLoading(false); return;
        }
        if (new Date(appointmentDateStr + 'T' + appointmentTimeStr) < new Date()) {
            showToast('Cannot book appointments in the past.', 'error'); setLoading(false); return;
        }

        const appointmentId = $('#appointment-id').val();
        let url = appointmentId ? `/reschedule/${appointmentId}` : '/book';
        const formData = {
            patient_name: $('#patient-name').val(), patient_age: $('#patient-age').val(),
            patient_gender: $('#patient-gender').val(), patient_contact: $('#patient-contact').val(),
            department: $('#appointment-department').val(), appointment_date: appointmentDateStr,
            appointment_time: appointmentTimeStr, new_date: appointmentDateStr, new_time: appointmentTimeStr,
        };

        $.ajax({
            type: 'POST', url: url, contentType: 'application/json', data: JSON.stringify(formData),
            success: function(data) {
                showToast(data.message, 'success');
                refreshAppointments();
                resetForm();
                // ## NEW: Automatically switch to view appointments after booking ##
                $('#appointments-view-btn').click();
            },
            error: function(xhr) { showToast(xhr.responseJSON?.message || 'An unknown error occurred.', 'error'); },
            complete: function() { setLoading(false); }
        });
    });

    $('#appointments-list').on('click', '.cancel-btn', function(e) {
        e.stopPropagation();
        const listItem = $(this).closest('.appointment-item');
        const appointmentId = listItem.data('id');
        if (confirm('Are you sure you want to cancel this appointment?')) {
            $.ajax({
                type: 'GET', url: `/cancel/${appointmentId}`,
                success: function(data) { showToast(data.message, 'success'); refreshAppointments(); },
                error: function(xhr) { showToast(xhr.responseJSON?.message, 'error'); }
            });
        }
    });

    // ## UPDATED: Reschedule button now also switches view ##
    $('#appointments-list').on('click', '.reschedule-btn', function(e) {
        e.stopPropagation();
        const listItem = $(this).closest('.appointment-item');
        const appointmentId = listItem.data('id');
        
        $('#appointments-list').find('.is-editing').removeClass('is-editing');

        $.ajax({
            type: 'GET', url: `/api/appointment/${appointmentId}`,
            success: function(appointment) {
                if(appointment.error) { showToast(appointment.error, 'error'); return; }
                
                // ## NEW: Automatically switch to the booking view ##
                $('#book-view-btn').click(); 
                listItem.addClass('is-editing');
                
                $('#form-title').text(`Editing: ${appointment.patient_name}`);
                $('#cancel-edit-btn').show();
                const btn = $('#form-submit-btn');
                btn.html('<span class="spinner"></span><span class="btn-text"><i class="fas fa-edit"></i> Confirm Changes</span>');
                btn.removeClass('btn-primary').addClass('btn-warning');

                $('#appointment-id').val(appointmentId);
                $('#patient-name').val(appointment.patient_name);
                $('#patient-age').val(appointment.patient_age);
                $('#patient-gender').val(appointment.patient_gender);
                $('#patient-contact').val(appointment.patient_contact);
                $('#appointment-department').val(appointment.department);
                $('#appointment-date').val(appointment.appointment_date);
                $('#appointment-time').val(appointment.appointment_time);
            },
            error: function() { showToast('Could not fetch appointment details.', 'error'); }
        });
    });

    $('#cancel-edit-btn').on('click', function() {
        resetForm();
    });

    function sendMessage() {
        const message = $('#user-input').val().trim();
        if (message) {
            $('#chat-window').append(`<div class="message message-user">${message}</div>`);
            $('#user-input').val('');
            $('#chat-window').scrollTop($('#chat-window')[0].scrollHeight);
            $.ajax({
                type: 'POST', url: '/chat', contentType: 'application/json',
                data: JSON.stringify({ message: message }),
                success: function(data) {
                    $('#chat-window').append(`<div class="message message-bot">${data.response}</div>`);
                    $('#chat-window').scrollTop($('#chat-window')[0].scrollHeight);
                },
                error: function() { showBotMessage("Sorry, I'm having trouble connecting."); }
            });
        }
    }
    $('#send-btn').click(sendMessage);
    $('#user-input').keypress(function(e) { if (e.which == 13) sendMessage(); });

    // Initial Load
    refreshAppointments();
});