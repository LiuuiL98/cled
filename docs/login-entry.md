# Login entry locator notes

The screenshot identifies the account/password mode switch as a folded-corner lock icon in the upper-right corner of the white login panel. The entry has no visible text label. The desktop automation should locate the panel using the two visible login tabs ("易学堂登录" and "云助理登录"), then inspect the panel's upper-right corner for the clickable icon. It must require a single candidate before clicking and stop rather than guess when the DOM differs.
