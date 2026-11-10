<?php

declare(strict_types=1);
return ['routes' => [
    ['name' => 'page#index', 'url' => '/', 'verb' => 'GET'],
    ['name' => 'page#bootstrap', 'url' => '/bootstrap', 'verb' => 'POST'],
    ['name' => 'page#sessionStatus', 'url' => '/session-status', 'verb' => 'GET'],
]];
