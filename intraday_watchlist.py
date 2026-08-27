INTRADAY_SYMBOLS = [
    "LLOYDSME", "VMM", "KRBL", "ZAGGLE", "MARUTI", "M&M",
    "HYUNDAI", "LENSKART", "ATULAUTO", "ASTRAL", "BEL", "GLAND",
    "JUBLFOOD", "COALINDIA", "POONAWALLA", "KAJARIACER", "ETERNAL", "GRASIM",
    "VINATIORGA", "APLAPOLLO", "GOKEX", "BHARTIHEXA", "HINDALCO", "STARHEALTH",
    "AHLUCONT", "ADANIPORTS", "MOTHERSON", "SUPRAJIT", "ZFCVINDIA", "MSUMI",
    "ENDURANCE", "ASKAUTOLTD", "ARE&M", "UNOMINDA", "AGARWALEYE", "RATNAVEER",
    "ACE", "JIOFIN", "GRSE", "NORTHARC", "RATEGAIN", "PIDILITIND",
    "AVALON", "SHRIRAMFIN", "UPL", "ICICIGI", "RELIANCE", "SUNFLAG",
    "HINDCOPPER", "NYKAA", "SBIN", "SBILIFE", "ICICIBANK", "SANDUMA",
    "MEESHO", "UNITDSPR", "SAGILITY", "HINDZINC", "CUMMINSIND", "RHIM",
    "SAATVIKGL", "DIVISLAB", "ZYDUSLIFE", "PPLPHARMA", "COHANCE", "ANTHEM",
    "MARKSANS", "NEULANDLAB", "NETWEB", "ANANTRAJ", "TECHNOE",
    "SUPREMEIND", "APOLLOPIPE", "POLYCAB", "CARYSIL", "DELHIVERY", "APOLLO",
    "KALYANKJIL", "GOPAL", "SOMANYCERA", "SONACOMS", "ABB", "ICIL",
    "SIGNATURE", "SANDHAR", "SUNTECK", "BOMDYEING", "AJMERA", "HUDCO",
    "LODHA", "GODREJPROP", "SOBHA", "OBEROIRLTY", "BRIGADE", "DBREALTY",
    "MANKIND", "MOIL", "GMRAIRPORT", "AURIONPRO", "CENTUM", "KEI",
    "BDL", "ROUTE", "PRECWIRE", "SOLARINDS", "TATAPOWER", "ARVINDFASN",
    "OSWALPUMPS", "TAJGVK", "PRESTIGE", "BANSALWIRE", "GULFOILLUB", "HBLENGINE",
    "CEMPRO", "MIDWESTLTD", "ATLANTAELE", "BALUFORGE", "AARTIIND", "AEGISLOG",
    "ZENTEC", "PARAS", "MAZDOCK", "SYRMA", "DATAPATTNS", "COCHINSHIP",
    "HAL", "ASTRAMICRO", "STLTECH", "GRINDWELL", "SANSERA", "WAAREEENER",
    "TIPSMUSIC", "CUPID", "TDPOWERSYS", "MTARTECH", "DIACABS", "AETHER",
    "SHRIPISTON", "VENTIVE", "CENTURYPLY", "KANSAINER", "SUDARSCHEM", "TRIVENI",
    "GNFC", "SRF", "MSTCLTD", "UJJIVANSFB", "GMMPFAUDLR", "BAJAJELEC",
    "JSFB", "MFSL", "RUBICON", "TI", "GPPL", "AZAD", "HAPPSTMNDS", "VOLTAMP",
    "BALAMINES", "VAML", "KIRLOSENG", "AMBUJACEM", "SHILPAMED", "INDIGOPNTS",
    "KIRLPNU", "NEOGEN", "MANORAMA", "GODREJAGRO", "ASTERDM", "BLUESTARCO",
    "CASTROLIND", "CDSL", "ANGELONE", "RADICO", "CAMS", "CHAMBLFERT",
    "CROMPTON", "KARURVYSYA", "CHALET", "MANAPPURAM", "LEMONTREE", "FSL",
    "MCX", "PNBHOUSING", "NATIONALUM", "NAVINFLUOR", "INDHOTEL", "EIHOTEL",
    "ROHLTD", "WELCORP", "RAMCOCEM", "REDINGTON", "KFINTECH", "PGEL",
    "CYIENTDLM", "BBOX", "WABAG", "TRANSRAILL", "ARTEMISMED", "NBCC",
    "JSL", "VTL", "LUMAXTECH", "CRAFTSMAN", "TORNTPOWER", "ADANIENSOL",
    "JSWENERGY", "ADANIGREEN", "NTPC", "POWERGRID", "THYROCARE", "CONCORDBIO",
    "IPCALAB", "NH", "VIJAYA", "ARVIND", "BIOCON", "GRAVITA", "JINDALSAW",
    "ENGINERSIN", "RML", "GARFIBRES", "RAINBOW", "RRKABEL", "CARTRADE",
    "LANDMARK", "ZENSARTECH", "BALKRISIND", "THERMAX", "CLEAN", "IDEAFORGE",
    "ASHOKLEY", "RKFORGE", "IGIL", "GPIL", "KPIL", "SHAKTIPUMP",
    "RVNL", "IRFC", "PFC", "USHAMART", "NMDC", "HONASA", "TARIL", "VSSL",
    "GODREJIND", "SAILIFE", "CEATLTD", "SCHNEIDER", "AADHARHFC", "JKCEMENT",
    "360ONE", "ACMESOLAR", "TEGA", "ELGIEQUIP", "PCBL", "LCL",
    "BEML", "ASAHIINDIA", "SCI", "JARO", "PWL", "VERANDA", 
    "WELSPUNLIV", "KPRMILL", "PERSISTENT", "COFORGE", "INDIGO", "ABCAPITAL",
    "TVSMOTOR", "BAJAJ-AUTO", "TATACOMM", "WINDLAS", "AMRUTANJAN", "PFIZER",
    "ASIANPAINT", "INGERRAND", "WALCHANNAG", "AMAGI", "TITAGARH", "MANIPALHOS", "TATACAP",
    "NAM-INDIA", "EMMVEE", "FINEORG", "GABRIEL", "GRWRHITECH", "ITCHOTELS",
    "JBMA", "MINDACORP", "PRIVISCL", "DMART", "SHYAMMETL", "FMGOETZE",
    "URBANCO", "SUMICHEM", "ZYDUSWELL", "TRAVELFOOD", "SHANTIGEAR",

    # Added from NIFTY 50 + NIFTY Financial Services (official NSE index
    # constituent lists), deduped against the symbols already above.
    "ADANIENT", "APOLLOHOSP", "AXISBANK", "BAJAJFINSV", "BAJFINANCE",
    "BHARTIARTL", "BSE", "CHOLAFIN", "CIPLA", "DRREDDY", "EICHERMOT",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HINDUNILVR", "INFY", "ITC",
    "JSWSTEEL", "KOTAKBANK", "LICHSGFIN", "LT", "MAXHEALTH", "MUTHOOTFIN",
    "NESTLEIND", "ONGC", "RECLTD", "SBICARD", "SUNPHARMA", "TATACONSUM",
    "TATASTEEL", "TCS", "TECHM", "TITAN", "TMPV", "TRENT", "ULTRACEMCO",
    "WIPRO",

    # Pharma/CDMO + hospital: NIFTY Pharma + NIFTY Healthcare (official NSE
    # index lists) plus dedicated CDMO/hospital names from general knowledge
    # (not from an official index -- worth a spot-check).
    "ABBOTINDIA", "AJANTPHARM", "ALKEM", "AUROPHARMA", "FORTIS", "GLENMARK",
    "LAURUSLABS", "LUPIN", "SYNGENE", "TORNTPHARM", "WOCKPHARMA",
    "AARTIPHARM", "HIKAL", "SUVENPHAR", "GLOBALHEALTH", "KIMS", "SHALBY",
    "YATHARTH",

    # Textiles (general knowledge, not an official index -- worth a spot-check).
    "TRIDENT", "RAYMOND", "PAGEIND", "SUTLEJTEX", "SIYSIL", "NITINSPIN",
    "HIMATSEIDE",

    # Hospitality/travel (general knowledge, not an official index -- worth a spot-check).
    "MHRIL", "SAMHI", "JUNIPER", "EASEMYTRIP", "THOMASCOOK", "WONDERLA",

    # Auto ancillaries: NIFTY Auto (official NSE index, includes OEMs +
    # top ancillaries) plus additional dedicated ancillary names from
    # general knowledge (not from an official index -- worth a spot-check).
    "BHARATFORG", "BOSCHLTD", "EXIDEIND", "HEROMOTOCO", "TIINDIA",
    "AMARAJABAT", "APOLLOTYRE", "AUTOAXLES", "FIEMIND", "JAMNAAUTO",
    "LUMAXIND", "MAHINDCIE", "MRF", "RAJRATAN", "RANEBRAKE", "RANEHOLDIN",
    "RICOAUTO", "SSWL", "SUBROS", "SUNDRMFAST", "VARROC",

    # Data center theme (genuinely niche in listed Indian markets -- most
    # pure-play data center operators aren't public; these are the closest
    # listed proxies, from general knowledge not an official index).
    "SIFY", "RAILTEL", "KAYNES",

    # Construction/housing/railway/bridges + ancillaries (cement, paint,
    # tiles, pipes): NIFTY Realty + NIFTY Infra (official NSE index lists)
    # plus dedicated names from general knowledge (not an official index --
    # worth a spot-check).
    "ABREL", "BPCL", "CGPOWER", "DLF", "GAIL", "HINDPETRO", "INDUSTOWER",
    "IOC", "PHOENIXLTD", "SHREECEM", "SUZLON",
    "ACC", "AKZOINDIA", "ASHOKA", "BERGEPAINT", "BIRLACORPN", "CERA",
    "DALBHARAT", "DBL", "FINPIPE", "GRINFRA", "INDIACEM", "IRB", "IRCON",
    "ITDCEM", "JKIL", "JKLAKSHMI", "KEC", "KNRCON", "NCC", "NITCO",
    "NUVOCO", "ORIENTBELL", "PNCINFRA", "PRINCEPIPE", "RITES",
    "STARCEMENT", "TEXRAIL",

    # Added by explicit request after showing up in MODI3's order-win/
    # results news coverage (JBFIND, CEIGALL, AHLWEST) plus two more asked
    # for directly (PITTIENG, VEDL).
    "JBFIND", "CEIGALL", "AHLWEST", "PITTIENG", "VEDL",

    # Added by explicit request (large batch). A few needed correcting from
    # the names given: MOLDTEKPACK -> MOLDTKPAC, CAPPACIT INFRA -> CAPACITE,
    # TATA TECHNOLOGY -> TATATECH, AIA -> AIAENG, NEPHROCARE -> NEPHROPLUS,
    # IFB -> IFBIND, KIRLOSBRO -> KIRLOSBROS, RAYMONREL -> RAYMONDREL.
    # "JIOFINBELRISE" and "SPALSUMICHEM" were two names run together without
    # a comma -- split into BELRISE (JIOFIN was already on the list) and
    # SPAL + SUMICHEM (SUMICHEM was already on the list) respectively.
    "JKPAPER", "AUBANK", "MAHSEAMLES", "AVANTIFEED", "BASF", "RAIN",
    "MOLDTKPAC", "CAPACITE", "JSWINFRA", "TATATECH", "AIAENG", "BELRISE",
    "ATHERENERG", "NEPHROPLUS", "MANINFRA", "CIEINDIA", "DOMS", "ENRIN",
    "ENTERO", "EPACK", "GVT&D", "HARSHA", "HEG", "HIRECT", "IFBIND",
    "INTELLECT", "KIRLOSBROS", "KRISHANA", "LALPATHLAB", "MAHLIFE",
    "MIDHANI", "POWERMECH", "RAYMONDLSL", "RAYMONDREL", "SAFARI", "SIS",
    "SOUTHBANK", "SPAL", "SKFINDIA", "SJS", "SHANKARA",
]