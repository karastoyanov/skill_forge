// Invite Guild member functionality
document.getElementById('inviteButton').addEventListener('click', function() {
    var div = document.getElementById('invMemberBody');
    if (div.classList.contains('hidden')) {
        div.classList.remove('hidden');
    } else {
        div.classList.add('hidden');
    }
});


// Kikc Guild member functionality
document.getElementById('kickButton').addEventListener('click', function() {
    var div = document.getElementById('kickMemberBody');
    if (div.classList.contains('hidden')) {
        div.classList.remove('hidden');
    } else {
        div.classList.add('hidden');
    }
});


