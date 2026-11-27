"""Fixed wording for the rule-based plan shown when Gemini is unavailable.

English and Hindi text live here so logic.py stays focused on the calculations.
Placeholders such as {pm} or {hours} are filled in by logic.offline_plan().
"""

# Hindi names for AQI categories, commute modes and masks.
HI_CAT = {"good": "अच्छी", "moderate": "मध्यम", "usg": "संवेदनशील समूहों के लिए अस्वास्थ्यकर",
          "unhealthy": "अस्वास्थ्यकर", "very_unhealthy": "बहुत अस्वास्थ्यकर", "hazardous": "खतरनाक"}
HI_MODE = {"car": "कार", "two_wheeler": "दोपहिया", "auto": "ऑटो-रिक्शा", "bus": "बस",
           "metro": "मेट्रो", "cycle_walk": "साइकिल / पैदल"}
HI_MASK = {"none": "कोई नहीं", "cloth": "कपड़े का", "surgical": "सर्जिकल", "n95": "N95"}

HH_TEXT = {
    "en": {
        "commuter": "Plan your commute carefully: timing, a well-fitted mask and combining trips matter most.",
        "young_children": "Children breathe faster and are more sensitive: keep play indoors on bad days and keep the air clean where they sleep.",
        "seniors": "Older adults are more sensitive: limit morning walks on bad days, keep medicines handy and use one clean-air room.",
        "student_athlete": "Move hard training indoors or to the cleanest hours, and avoid intense exercise near traffic.",
        "gig_worker": "You spend long hours outdoors: wear a well-fitted N95, take breaks in cleaner indoor spots and avoid heavy-traffic roads where you can.",
    },
    "hi": {
        "commuter": "आने-जाने पर ध्यान दें: समय, साधन बदलना, मास्क की फ़िटिंग और चक्कर मिलाना।",
        "young_children": "बच्चे तेज़ साँस लेते हैं और ज़्यादा संवेदनशील होते हैं: खराब दिनों में खेल घर के अंदर रखें और उनके सोने के कमरे में साफ़ हवा रखें।",
        "seniors": "बुज़ुर्ग ज़्यादा संवेदनशील होते हैं: खराब दिनों में सुबह की सैर सीमित करें, दवाइयाँ/इनहेलर पास रखें और एक साफ़-हवा वाला कमरा रखें।",
        "student_athlete": "भारी अभ्यास घर के अंदर या सबसे साफ़ घंटों में करें; AQI ज़्यादा हो तो ट्रैफ़िक के पास तेज़ कसरत से बचें।",
        "gig_worker": "बाहर लंबे घंटे: ठीक से फिट N95, साफ़ जगहों पर ब्रेक, और संभव हो तो भारी ट्रैफ़िक से दूर के रास्ते।",
    },
}

OFFLINE = {
    "en": dict(
        heads=["1. Right now", "2. Low-emission daily routine", "3. Indoor air",
               "4. Sustainable swap", "5. Extra care for this household"],
        why="Why it helps:",
        now="The air is {cat} right now (PM2.5 {pm} µg/m3), so plan your day around it.",
        now_why="Fine particles go deep into the lungs, and a higher reading means you breathe in more of them.",
        asthma="Someone in your household has asthma: keep the inhaler and medicines within reach and stay indoors during the worst hours.",
        asthma_why="Fine particles can trigger breathing trouble in people with asthma.",
        hours="Do outdoor trips and exercise at the cleanest hours: {hours}.",
        hours_why="The forecast shows lower pollution then, so you breathe in fewer particles.",
        n95="Wear a well-fitted N95 outdoors.",
        n95_why="Compared with your current mask ({mask}), it would cut roughly {pct}% of the fine particles you breathe in outdoors (estimate).",
        n95_keep="You already wear an N95: keep it tight on your face and replace it when worn out.",
        n95_keep_why="Gaps around the edges let unfiltered air in.",
        combine="Combine errands into one trip and avoid peak traffic.",
        combine_why="Fewer trips mean less time breathing exhaust fumes on the road.",
        pur_have="Keep your purifier running in the room you use most, with doors and windows closed.",
        pur_have_why="Your purifier removes roughly {pct}% of indoor PM2.5 in a {room} m2 room (estimate).",
        pur_none="Pick one room (such as the bedroom) as a clean-air room and seal gaps around its windows and doors. A 250 m3/h purifier would help.",
        pur_none_why="A 250 m3/h unit would cut roughly {pct}% of indoor PM2.5 in a {room} m2 room (estimate).",
        vent="Open windows only at the cleanest outdoor hour, and use the kitchen exhaust while cooking.",
        vent_why="Cooking smoke adds fine particles indoors, and airing out when outdoor air is cleaner lets in less pollution.",
        swap="Try {to} instead of {frm} for your {km} km one-way commute when you can.",
        swap_why="It saves about {kg} kg CO2 per week (estimate, assuming a 5-day week) and cuts road emissions.",
        home="Avoid burning waste or incense indoors, and damp-mop instead of dry sweeping.",
        home_why="Smoke and stirred-up dust add fine particles to the air you breathe at home.",
        hh_why="Different households face different risks, so these tips target yours.",
        closing="This plan was built from live data and simple estimates because the AI service is busy. General guidance, not medical advice.",
    ),
    "hi": dict(
        heads=["1. अभी क्या करें", "2. कम प्रदूषण वाली दिनचर्या", "3. घर के अंदर की हवा",
               "4. टिकाऊ बदलाव", "5. आपके परिवार के लिए खास ध्यान"],
        why="यह क्यों मदद करता है:",
        now="अभी हवा {cat} है (PM2.5 {pm} µg/m3), इसलिए अपना दिन उसी के हिसाब से बनाएँ।",
        now_why="महीन कण फेफड़ों में गहराई तक जाते हैं, और रीडिंग जितनी ज़्यादा, उतने ज़्यादा कण साँस में जाते हैं।",
        asthma="घर में किसी को अस्थमा है: इनहेलर और दवाइयाँ पास रखें और सबसे खराब घंटों में घर के अंदर रहें।",
        asthma_why="महीन कण अस्थमा वाले लोगों में साँस की तकलीफ़ बढ़ा सकते हैं।",
        hours="बाहर के काम और कसरत सबसे साफ़ घंटों में करें: {hours}।",
        hours_why="पूर्वानुमान के अनुसार तब प्रदूषण कम रहेगा, इसलिए कम कण साँस में जाएँगे।",
        n95="बाहर ठीक से फिट होने वाला N95 पहनें।",
        n95_why="आपके मौजूदा मास्क ({mask}) की तुलना में इससे बाहर साँस में जाने वाले महीन कण लगभग {pct}% कम हो सकते हैं (अनुमान)।",
        n95_keep="आप पहले से N95 पहनते हैं: उसे चेहरे पर कसकर रखें और घिस जाए तो बदल लें।",
        n95_keep_why="किनारों के खाली हिस्सों से बिना छनी हवा अंदर आ जाती है।",
        combine="कई छोटे काम एक ही चक्कर में निपटाएँ और भीड़ के समय से बचें।",
        combine_why="कम चक्कर यानी सड़क पर धुएँ में कम समय।",
        pur_have="अपना प्यूरिफायर उस कमरे में चलाएँ जहाँ आप सबसे ज़्यादा रहते हैं, दरवाज़े-खिड़कियाँ बंद रखकर।",
        pur_have_why="आपका प्यूरिफायर {room} m2 के कमरे में घर के अंदर PM2.5 लगभग {pct}% घटाता है (अनुमान)।",
        pur_none="एक कमरे (जैसे बेडरूम) को साफ़-हवा वाला कमरा बनाएँ और उसकी खिड़कियों-दरवाज़ों की दरारें बंद करें। 250 m3/h का प्यूरिफायर मदद करेगा।",
        pur_none_why="250 m3/h का प्यूरिफायर {room} m2 के कमरे में घर के अंदर PM2.5 लगभग {pct}% घटा सकता है (अनुमान)।",
        vent="खिड़कियाँ केवल बाहर की हवा के सबसे साफ़ घंटे में खोलें और खाना बनाते समय चिमनी/एग्ज़ॉस्ट चलाएँ।",
        vent_why="खाना बनाने का धुआँ घर में महीन कण बढ़ाता है, और बाहर की हवा साफ़ होने पर हवा बदलने से कम प्रदूषण अंदर आता है।",
        swap="{km} किमी के एक तरफ़ के सफ़र में जब हो सके {frm} की जगह {to} अपनाएँ।",
        swap_why="इससे सप्ताह में लगभग {kg} किग्रा CO2 बचता है (अनुमान, सप्ताह में 5 दिन मानकर) और सड़क का उत्सर्जन घटता है।",
        home="घर के अंदर कचरा या धूप-अगरबत्ती न जलाएँ और झाड़ू की जगह गीले कपड़े से पोंछा लगाएँ।",
        home_why="धुआँ और उड़ती धूल घर की हवा में महीन कण बढ़ाते हैं।",
        hh_why="अलग-अलग परिवारों को अलग जोखिम होते हैं, इसलिए ये सुझाव आपके परिवार के हिसाब से हैं।",
        closing="AI सेवा व्यस्त होने के कारण यह योजना लाइव डेटा और सरल अनुमानों से बनी है। यह सामान्य सलाह है, चिकित्सकीय सलाह नहीं।",
    ),
}