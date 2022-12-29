<?php

declare(strict_types=1);

$valid = true;

$slash = DIRECTORY_SEPARATOR;

$composerJsonString = file_get_contents(__DIR__ . $slash . 'composer.json');
$composerJsonArray = json_decode($composerJsonString, true);
$autoloadString = key($composerJsonArray['autoload']['psr-4']);
$autoloadInfo = array_filter(explode('\\', $autoloadString));

$creator = $autoloadInfo[0];
$project = $autoloadInfo[1];

$prefix = $creator . $slash . $project . $slash;

$directoryToBeInspected = __DIR__ . $slash . 'src';
$iterator = new RecursiveDirectoryIterator($directoryToBeInspected);

/** @var SplFileInfo $file */
foreach (new RecursiveIteratorIterator($iterator) as $file) {
    if ($file->getExtension() == 'php') {
        $fullPath = $file->getPath() . $slash . $file->getFilename();

        $fileContent = file($fullPath);
        if ($fileContent === false) {
            continue;
        }

        $fullNamespace = '';
        foreach ($fileContent as $line) {
            if (str_contains($line, 'namespace ' . $prefix)) {
                $fullNamespace = $line;
                break;
            }
        }

        $namespace = match (true) {
            str_contains($fullNamespace, 'namespace ' . $prefix . 'Infrastructure') => 'Infrastructure',
            str_contains($fullNamespace, 'namespace ' . $prefix . 'App') => 'App',
            str_contains($fullNamespace, 'namespace ' . $prefix . 'Domain') => 'Domain',
            default => 'continue'
        };
        if ($namespace === 'continue') {
            continue;
        }

        $useStatements = [];
        foreach ($fileContent as $line) {
            $short = match (true) {
                str_contains($line, 'use ' . $prefix . 'Infrastructure') => 'Infrastructure',
                str_contains($line, 'use ' . $prefix . 'App') => 'App',
                str_contains($line, 'use ' . $prefix . 'Domain') => 'Domain',
                default => 'continue'
            };

            if ($short === 'continue') {
                continue;
            }

            $useStatements[] = [
                'short' => $short,
                'full' => $line,
            ];
        }
        if (empty($useStatements)) {
            continue;
        }

        $taboos = match ($namespace) {
            'Infrastructure' => ['Domain'],
            'App' => ['Infrastructure'],
            'Domain' => ['App', 'Infrastructure'],
        };

        $first = true;
        foreach ($useStatements as $useStatement) {
            if (in_array($useStatement['short'], $taboos)) {
                if ($first) {
                    $first = false;
                    $valid = false;

                    echo PHP_EOL, 'This file in ' . $namespace . ' uses ' . $useStatement['short'] . ' classes:', PHP_EOL, $fullPath, PHP_EOL;
                }

                echo $useStatement['full'];
            }
        }
    }
}

if ($valid) {
    echo 'Success! ', chr(9), 'No "use"-statements inappropriate in the context of DDD could be found.';
}

return $valid;
