
// Toggles display for up to 6 elements by ID
function display_toggle(t1, t2, t3, t4, t5, t6) {

    var toggles = [
        v1 = document.getElementById(t1),
        v2 = document.getElementById(t2),
        v3 = document.getElementById(t3),
        v4 = document.getElementById(t4),
        v5 = document.getElementById(t5),
        v6 = document.getElementById(t6)
    ];

    for (let i = 0; i < toggles.length; i++) {
        if (toggles[i].style.display === '') {
            toggles[i].style.display = 'none';
        }
        else {
            toggles[i].style.display = '';
        }
    }
}

// Set background color of 'avail' tds in budget table
function avail_bg(goal, goal_met, goal_spent, avail, field_id, check_icon, fund_button) {

    avail_color = document.getElementById(field_id);
    check = document.getElementById(check_icon);
    fund = document.getElementById(fund_button);


    if (goal != 0.0) {
        if (goal_met == 1) {
            if (goal_spent == 1) {
                if (avail == 0) {
                    // Grey
                    avail_color.style.backgroundColor = 'lightgrey';
                    check.style.display = '';
                    fund.style.display = 'none';
                }
                else {
                    // Goal fully spent, but additional funds added, so turn back to Green
                    avail_color.style.backgroundColor = 'rgb(92, 217, 92)';
                    check.style.display = '';
                    fund.style.display = 'none';
                }

            }
            else {
                // Fully funded and not fully spent: Green
                avail_color.style.backgroundColor = 'rgb(120, 217, 120)';
                check.style.display = '';
                fund.style.display = 'none';
            }
        }
        else {
            // Not fully funded: Yellow
            avail_color.style.backgroundColor = 'rgb(255, 249, 136)';
            // 237, 251, 107
        }
    }

    else {
        // In this case, there is no goal set for the category, so do not show the fund button
        fund.style.display = 'none';
    }
}

function avatarValidation() {

    // Get user's uploaded image
    avatar = document.getElementById('avatar_file');

    // Get the string value of the file name
    filePath = avatar.value;

    // Set regex
    allowed = /(\.jpg|\.png|\.jpeg)$/i;

    // Match file extension to regex
    if (!allowed.exec(filePath)) {
        alert('Invalid file type. Please choose from: .jpg .png .jpeg');
        avatar.value = '';
        return false;
    }
}