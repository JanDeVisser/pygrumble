/*
 * Copyright (c) 2014-2018 Jan de Visser (jan@sweattrails.com)
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc., 51
 * Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 */

 function login_error(errorinfo) {
     if (errorinfo !== 401) return false;
     this.$["password"].clear();
     this.header.error("Mistyped email or password");
     this.footer.error();
     return true;
 }

 function signup_submitted() {
     st_alert("Your signup request is being processed. Check your email for further instructions.");
 }

 function password_changed() {
     st_alert("Your password is changed. Remember to use your new password the next time you check in.");
 }
