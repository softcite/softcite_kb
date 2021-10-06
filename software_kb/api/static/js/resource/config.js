var defaults = {
    // disambiguation
    host_nerd: "cloud.science-miner.com",
    port_nerd: "",

    // proxy
    service: "local", // access to service can be local or proxy, depending on security requirements
    proxy_host: "",
    
    // elasticsearch
    es_host : 'http://0.0.0.0:8050/search',
    fulltext_index: 'software-kb', // the URL against which to submit searches
    nerd_annotation_index: 'annotations_nerd',
    kb_index: 'software-kb',
    authors_type: 'authors',
    publications_type: 'publications',
    organisations_type: 'organisations',
    search_index: 'elasticsearch',
    
    kb_service_host: 'http://0.0.0.0:8050',
    //kb_service_host: 'http://192.168.1.106:8050',
    //kb_service_port: 8050,

    // a query parameter added to each query to the search engine
    query_parameter: "q", // the query parameter if required for setting to the search URL
    
    // the type of the main collection
    collection: 'npl',

    // the name of the sub-collection to be searched 
    subcollection: 'cord-19',

    // snippet ranking
    snippet_style: 'andlauer',
    
    // in case search is triggered automatically
    freetext_submit_delay: "400", // delay for auto-update of search results in ms
    use_delay: false, // if true, searches are triggered by keyup events with the above delay
                     // otherwise search is triggered by pressing enter
    
    display_images: true, // whether or not to display images found in links in search results    
    
    config_file: false, // a remote config file URL
    
    addremovefacets: false, // false if no facets can be added at front en
    
    visualise_filters: true, // whether or not to allow filter vis via d3
        
    default_url_params: {}, // any params that the search URL needs by default
    q: "", // default query value
    //query_field: "",
    
    predefined_filters: {}, // predefined filters to apply to all searches
    
    paging: {
        from: 0,    // where to start the results from
        size: 12    // how many results to get
    },
    
    mode_query: "simple", // query input, possible values: simple, complex, nl, semantic, analytics
    
    complex_fields: 0, // number of fields introduced in the complex query form
    
    // wikipedia image service
    wikimediaURL_EN: 'https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&pithumbsize=200&pageids=',
    wikimediaURL_FR: 'https://fr.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&pithumbsize=200&pageids=',
    wikimediaURL_DE: 'https://de.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&pithumbsize=200&pageids=',
    
    imgCache: {}
};


